#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
import os, Queue, socket, time, types
from heapq import heappush, heappop, nsmallest
from . import Collector, Connection, ConnectionException, Delivery, Described, dispatch
from . import Endpoint, Event, EventType, generate_uuid, Handler, Link, Message
from . import ProtonException, PN_ACCEPTED, PN_PYREF, SASL, Session, symbol
from . import Terminus, Timeout, Transport, TransportException, ulong, Url
from select import select
from .handlers import nested_handlers, ScopedHandler

class AmqpSocket(object):
    """
    Associates a transport with a connection and a socket and can be
    used in an io loop to track the io for an AMQP 1.0 connection.
    """

    def __init__(self, conn, sock, events, heartbeat=None):
        self.events = events
        self.conn = conn
        self.transport = Transport()
        if heartbeat: self.transport.idle_timeout = heartbeat
        self.transport.bind(self.conn)
        self.socket = sock
        self.socket.setblocking(0)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.write_done = False
        self.read_done = False
        self._closed = False

    def accept(self, force_sasl=True):
        if force_sasl:
            sasl = self.transport.sasl()
            sasl.mechanisms("ANONYMOUS")
            sasl.server()
            sasl.done(SASL.OK)
        #TODO: use SASL anyway if requested by peer
        return self

    def connect(self, host, port=None, username=None, password=None, force_sasl=True):
        if username and password:
            sasl = self.transport.sasl()
            sasl.plain(username, password)
        elif force_sasl:
            sasl = self.transport.sasl()
            sasl.mechanisms('ANONYMOUS')
            sasl.client()
        try:
            self.socket.connect_ex((host, port or 5672))
        except socket.gaierror, e:
            raise ConnectionException("Cannot resolve '%s': %s" % (host, e))
        return self

    def _closed_cleanly(self):
        return self.conn.state & Endpoint.LOCAL_CLOSED and self.conn.state & Endpoint.REMOTE_CLOSED

    def closed(self):
        if not self._closed and self.write_done and self.read_done:
            self.close()
            return True
        else:
            return False

    def close(self):
        self.socket.close()
        self._closed = True

    def fileno(self):
        return self.socket.fileno()

    def reading(self):
        if self.read_done: return False
        c = self.transport.capacity()
        if c > 0:
            return True
        elif c < 0:
            self.read_done = True
        return False

    def writing(self):
        if self.write_done: return False
        try:
            p = self.transport.pending()
            if p > 0:
                return True
            elif p < 0:
                self.write_done = True
                return False
            else: # p == 0
                return False
        except TransportException, e:
            self.write_done = True
            return False

    def readable(self):
        c = self.transport.capacity()
        if c > 0:
            try:
                data = self.socket.recv(c)
                if data:
                    self.transport.push(data)
                else:
                    if not self._closed_cleanly():
                        self.read_done = True
                        self.write_done = True
                    else:
                        self.transport.close_tail()
            except TransportException, e:
                # TODO aconway 2014-12-11: log error: print "Error on read: %s" % e 
                self.read_done = True
            except socket.error, e:
                # TODO aconway 2014-12-11: log error: print "Error on recv: %s" % e
                self.read_done = True
                self.write_done = True
        elif c < 0:
            self.read_done = True

    def writable(self):
        try:
            p = self.transport.pending()
            if p > 0:
                data = self.transport.peek(p)
                n = self.socket.send(data)
                self.transport.pop(n)
            elif p < 0:
                self.write_done = True
        except TransportException, e:
            # TODO aconway 2014-12-11: log error: print "Error on write: %s" % e
            self.write_done = True
        except socket.error, e:
            # TODO aconway 2014-12-11: log error: print "Error on send: %s" % e
            self.write_done = True

    def removed(self):
        if not self._closed_cleanly():
            self.transport.unbind()
            self.events.dispatch(ApplicationEvent("disconnected", connection=self.conn))

    def tick(self):
        t = self.transport.tick(time.time())
        if t: return t
        else: return None

class AmqpAcceptor:
    """
    Listens for incoming sockets, creates an AmqpSocket for them and
    adds that to the list of tracked 'selectables'. The acceptor can
    itself be added to an io loop.
    """

    def __init__(self, events, loop, host, port):
        self.events = events
        self.loop = loop
        self.socket = socket.socket()
        self.socket.setblocking(0)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        self.socket.listen(5)
        self.loop.add(self)
        self._closed = False

    def closed(self):
        if self._closed:
            self.socket.close()
            return True
        else:
            return False

    def close(self):
        self._closed = True

    def fileno(self):
        return self.socket.fileno()

    def reading(self):
        return not self._closed

    def writing(self):
        return False

    def readable(self):
        sock, addr = self.socket.accept()
        if sock:
            self.loop.add(AmqpSocket(self.events.connection(), sock, self.events).accept())

    def removed(self): pass
    def tick(self): return None


class EventInjector(object):
    """
    Can be added to an io loop to allow events to be triggered by an
    external thread but handled on the event thread associated with
    the loop.
    """
    def __init__(self, collector):
        self.collector = collector
        self.queue = Queue.Queue()
        self.pipe = os.pipe()
        self._closed = False

    def trigger(self, event):
        self.queue.put(event)
        os.write(self.pipe[1], "!")

    def closed(self):
        return self._closed and self.queue.empty()

    def close(self):
        self._closed = True

    def fileno(self):
        return self.pipe[0]

    def reading(self):
        return True

    def writing(self):
        return False

    def readable(self):
        os.read(self.pipe[0], 512)
        while not self.queue.empty():
            event = self.queue.get()
            self.collector.put(event.context, event.type)

    def removed(self): pass
    def tick(self): return None

class PQueue:

    def __init__(self):
        self.entries = []

    def add(self, priority, task):
        heappush(self.entries, (priority, task))

    def peek(self):
        if self.entries:
            return nsmallest(1, self.entries)[0]
        else:
            return None

    def pop(self):
        if self.entries:
            return heappop(self.entries)
        else:
            return None

    def __nonzero__(self):
        if self.entries:
            return True
        else:
            return False

class Timer:
    def __init__(self, collector):
        self.collector = collector
        self.events = PQueue()

    def schedule(self, deadline, event):
        self.events.add(deadline, event)

    def tick(self):
        while self.events:
            deadline, event = self.events.peek()
            if time.time() > deadline:
                self.events.pop()
                self.collector.put(event.context, event.type)
            else:
                return deadline
        return None

    @property
    def pending(self):
        return bool(self.events)

class Events(object):
    def __init__(self, *handlers):
        self.collector = Collector()
        self.timer = Timer(self.collector)
        self.handlers = handlers

    def connection(self):
        conn = Connection()
        conn.collect(self.collector)
        return conn

    def process(self):
        result = False
        while True:
            ev = self.collector.peek()
            if ev:
                self.dispatch(ev)
                self.collector.pop()
                result = True
            else:
                return result

    def dispatch(self, event):
        for h in self.handlers:
            event.dispatch(h)

    @property
    def empty(self):
        return self.collector.peek() == None and not self.timer.pending

class Names(object):
    def __init__(self, base=10000):
        self.names = []
        self.base = base

    def number(self, name):
        if name not in self.names:
            self.names.append(name)
        return self.names.index(name) + self.base

class ExtendedEventType(EventType):
    USED = Names()
    """
    Event type identifier for events defined outside the proton-c
    library
    """
    def __init__(self, name, number=None):
        super(ExtendedEventType, self).__init__(number or ExtendedEventType.USED.number(name), "on_%s" % name)
        self.name = name

class ApplicationEventContext(object):
    def __init__(self, connection=None, session=None, link=None, delivery=None, subject=None):
        self.connection = connection
        self.session = session
        self.link = link
        self.delivery = delivery
        if self.delivery:
            self.link = self.delivery.link
        if self.link:
            self.session = self.link.session
        if self.session:
            self.connection = self.session.connection
        self.subject = subject

    def __repr__(self):
        objects = [self.connection, self.session, self.link, self.delivery, self.subject]
        return ", ".join([str(o) for o in objects if o is not None])

class ApplicationEvent(Event):
    """
    Application defined event, which can optionally be associated with
    an engine object and or an arbitrary subject
    """
    def __init__(self, typename, connection=None, session=None, link=None, delivery=None, subject=None):
        super(ApplicationEvent, self).__init__(PN_PYREF, ApplicationEventContext(connection, session, link, delivery, subject), ExtendedEventType(typename))

class StartEvent(ApplicationEvent):
    def __init__(self, container):
        super(StartEvent, self).__init__("start")
        self.container = container

def _min(a, b):
    if a and b: return min(a, b)
    elif a: return a
    else: return b

class SelectLoop(object):
    """
    An io loop based on select()
    """
    def __init__(self, events):
        self.events = events
        self.selectables = []
        self._abort = False

    def abort(self):
        self._abort = True

    def add(self, selectable):
        self.selectables.append(selectable)

    def remove(self, selectable):
        self.selectables.remove(selectable)

    @property
    def redundant(self):
        return self.events.empty and not self.selectables

    @property
    def aborted(self):
        return self._abort

    def run(self):
        while not (self._abort or self.redundant):
            self.do_work()

    def do_work(self, timeout=None):
        """@return True if some work was done, False if time-out expired"""
        tick = self.events.timer.tick()

        if self.events.process():
            tick = self.events.timer.tick()
            while self.events.process():
                if self._abort: return
                tick = self.events.timer.tick()
            return True # Did work, let caller check their conditions, don't select.

        stable = False
        while not stable:
            reading = []
            writing = []
            closed = []
            for s in self.selectables:
                if s.reading(): reading.append(s)
                if s.writing(): writing.append(s)
                if s.closed(): closed.append(s)
                else: tick = _min(tick, s.tick())

            for s in closed:
                self.selectables.remove(s)
                s.removed()
            stable = len(closed) == 0

        if self.redundant:
            return False

        if tick:
            timeout = _min(tick - time.time(), timeout)
        if timeout and timeout < 0:
            timeout = 0
        if reading or writing or timeout:
            readable, writable, _ = select(reading, writing, [], timeout)
            for s in self.selectables:
                s.tick()
            for s in readable:
                s.readable()
            for s in writable:
                s.writable()

            return bool(readable or writable)
        else:
            return False

def delivery_tags():
    count = 1
    while True:
        yield str(count)
        count += 1

def send_msg(sender, msg, tag=None, handler=None, transaction=None):
    dlv = sender.delivery(tag or next(sender.tags))
    if transaction:
        dlv.local.data = [transaction.id]
        dlv.update(0x34)
    if handler:
        dlv.context = handler
    sender.send(msg.encode())
    sender.advance()
    return dlv

def _send_msg(self, msg, tag=None, handler=None, transaction=None):
    return send_msg(self, msg, tag, handler, transaction)


class Transaction(object):
    """
    Class to track state of an AMQP 1.0 transaction.
    """
    def __init__(self, txn_ctrl, handler, settle_before_discharge=False):
        self.txn_ctrl = txn_ctrl
        self.handler = handler
        self.id = None
        self._declare = None
        self._discharge = None
        self.failed = False
        self._pending = []
        self.settle_before_discharge = settle_before_discharge
        self.declare()

    def commit(self):
        self.discharge(False)

    def abort(self):
        self.discharge(True)

    def declare(self):
        self._declare = self._send_ctrl(symbol(u'amqp:declare:list'), [None])

    def discharge(self, failed):
        self.failed = failed
        self._discharge = self._send_ctrl(symbol(u'amqp:discharge:list'), [self.id, failed])

    def _send_ctrl(self, descriptor, value):
        delivery = self.txn_ctrl.send_msg(Message(body=Described(descriptor, value)), handler=self.handler)
        delivery.transaction = self
        return delivery

    def accept(self, delivery):
        self.update(delivery, PN_ACCEPTED)
        if self.settle_before_discharge:
            delivery.settle()
        else:
            self._pending.append(delivery)

    def update(self, delivery, state=None):
        if state:
            delivery.local.data = [self.id, Described(ulong(state), [])]
            delivery.update(0x34)

    def _release_pending(self):
        for d in self._pending:
            d.update(Delivery.RELEASED)
            d.settle()
        self._clear_pending()

    def _clear_pending(self):
        self._pending = []

    def handle_outcome(self, event):
        if event.delivery == self._declare:
            if event.delivery.remote.data:
                self.id = event.delivery.remote.data[0]
                self.handler.on_transaction_declared(event)
            elif event.delivery.remote_state == Delivery.REJECTED:
                self.handler.on_transaction_declare_failed(event)
            else:
                # TODO aconway 2014-12-11: log error: print "Unexpected outcome for declare: %s" % event.delivery.remote_state
                self.handler.on_transaction_declare_failed(event)
        elif event.delivery == self._discharge:
            if event.delivery.remote_state == Delivery.REJECTED:
                if not self.failed:
                    self.handler.on_transaction_commit_failed(event)
                    self._release_pending() # make this optional?
            else:
                if self.failed:
                    self.handler.on_transaction_aborted(event)
                    self._release_pending()
                else:
                    self.handler.on_transaction_committed(event)
            self._clear_pending()

class LinkOption(object):
    """
    Abstract interface for link configuration options
    """
    def apply(self, link):
        """
        Subclasses will implement any configuration logic in this
        method
        """
        pass
    def test(self, link):
        """
        Subclasses can override this to selectively apply an option
        e.g. based on some link criteria
        """
        return True

class AtMostOnce(LinkOption):
    def apply(self, link):
        link.snd_settle_mode = Link.SND_SETTLED

class AtLeastOnce(LinkOption):
    def apply(self, link):
        link.snd_settle_mode = Link.SND_UNSETTLED
        link.rcv_settle_mode = Link.RCV_FIRST

class SenderOption(LinkOption):
    def apply(self, sender): pass
    def test(self, link): return link.is_sender

class ReceiverOption(LinkOption):
    def apply(self, receiver): pass
    def test(self, link): return link.is_receiver

class Filter(ReceiverOption):
    def __init__(self, filter_set={}):
        self.filter_set = filter_set

    def apply(self, receiver):
        receiver.source.filter.put_dict(self.filter_set)

class Selector(Filter):
    """
    Configures a link with a message selector filter
    """
    def __init__(self, value, name='selector'):
        super(Selector, self).__init__({symbol(name): Described(symbol('apache.org:selector-filter:string'), value)})

def _apply_link_options(options, link):
    if options:
        if isinstance(options, list):
            for o in options:
                if o.test(link): o.apply(link)
        else:
            if options.test(link): options.apply(link)

def _create_session(connection, handler=None):
    session = connection.session()
    session.open()
    return session


def _get_attr(target, name):
    if hasattr(target, name):
        return getattr(target, name)
    else:
        return None

class SessionPerConnection(object):
    def __init__(self):
        self._default_session = None

    def session(self, connection):
        if not self._default_session:
            self._default_session = _create_session(connection)
            self._default_session.context = self
        return self._default_session

    def on_session_remote_close(self, event):
        event.connection.close()
        self._default_session = None

class Connector(Handler):
    """
    Internal handler that triggers the necessary socket connect for an
    opened connection.
    """
    def __init__(self, loop):
        self.loop = loop

    def _connect(self, connection):
        host, port = connection.address.next()
        heartbeat = connection.heartbeat if hasattr(connection, 'heartbeat') else None
        self.loop.add(AmqpSocket(connection, socket.socket(), self.loop.events, heartbeat=heartbeat).connect(host, port))
        connection._pin = None #connection is now referenced by AmqpSocket, so no need for circular reference

    def on_connection_local_open(self, event):
        if hasattr(event.connection, "address"):
            self._connect(event.connection)

    def on_connection_remote_open(self, event):
        if hasattr(event.connection, "reconnect"):
            event.connection.reconnect.reset()

    def on_disconnected(self, event):
        if hasattr(event.connection, "reconnect"):
            event.connection._pin = event.connection #no longer referenced by AmqpSocket, so pin in memory with circular reference
            delay = event.connection.reconnect.next()
            if delay == 0:
                # TODO aconway 2014-12-11: log error: print "Disconnected, reconnecting..."
                self._connect(event.connection)
            else:
                # TODO aconway 2014-12-11: log error: print "Disconnected will try to reconnect after %s seconds" % delay
                self.loop.schedule(time.time() + delay, connection=event.connection, subject=self)
        else:
            # TODO aconway 2014-12-11: log error: print "Disconnected"
            pass

    def on_timer(self, event):
        if event.subject == self and event.connection:
            self._connect(event.connection)

class Backoff(object):
    """
    A reconnect strategy involving an increasing delay between
    retries, up to a maximum or 10 seconds.
    """
    def __init__(self):
        self.delay = 0

    def reset(self):
        self.delay = 0

    def next(self):
        current = self.delay
        if current == 0:
            self.delay = 0.1
        else:
            self.delay = min(10, 2*current)
        return current

class Urls(object):
    def __init__(self, values):
        self.values = [Url(v) for v in values]
        self.i = iter(self.values)

    def __iter__(self):
        return self

    def _as_pair(self, url):
        return (url.host, url.port)

    def next(self):
        try:
            return self._as_pair(self.i.next())
        except StopIteration:
            self.i = iter(self.values)
            return self._as_pair(self.i.next())

class Container(object):
    def __init__(self, *handlers):
        h = [Connector(self), ScopedHandler()]
        h.extend(nested_handlers(handlers))
        self.events = Events(*h)
        self.loop = SelectLoop(self.events)
        self.trigger = None
        self.container_id = str(generate_uuid())

    def connect(self, url=None, urls=None, address=None, handler=None, reconnect=None, heartbeat=None):
        conn = self.events.connection()
        conn._pin = conn #circular reference until the open event gets handled
        if handler:
            conn.context = handler
        conn.container = self.container_id or str(generate_uuid())
        conn.heartbeat = heartbeat
        if url: conn.address = Urls([url])
        elif urls: conn.address = Urls(urls)
        elif address: conn.address = address
        else: raise ValueError("One of url, urls or address required")
        if reconnect:
            conn.reconnect = reconnect
        elif reconnect is None:
            conn.reconnect = Backoff()
        conn._session_policy = SessionPerConnection() #todo: make configurable
        conn.open()
        return conn

    def _get_id(self, container, remote, local):
        if local and remote: "%s-%s-%s" % (container, remote, local)
        elif local: return "%s-%s" % (container, local)
        elif remote: return "%s-%s" % (container, remote)
        else: return "%s-%s" % (container, str(generate_uuid()))

    def _get_session(self, context):
        if isinstance(context, Url):
            return self._get_session(self.connect(url=context))
        elif isinstance(context, Session):
            return context
        elif isinstance(context, Connection):
            if hasattr(context, '_session_policy'):
                return context._session_policy.session(context)
            else:
                return _create_session(context)
        else:
            return context.session()

    def create_sender(self, context, target=None, source=None, name=None, handler=None, tags=None, options=None):
        if isinstance(context, basestring):
            context = Url(context)
        if isinstance(context, Url) and not target:
            target = context.path
        session = self._get_session(context)
        snd = session.sender(name or self._get_id(session.connection.container, target, source))
        if source:
            snd.source.address = source
        if target:
            snd.target.address = target
        if handler:
            snd.context = handler
        snd.tags = tags or delivery_tags()
        snd.send_msg = types.MethodType(_send_msg, snd)
        _apply_link_options(options, snd)
        snd.open()
        return snd

    def create_receiver(self, context, source=None, target=None, name=None, dynamic=False, handler=None, options=None):
        if isinstance(context, basestring):
            context = Url(context)
        if isinstance(context, Url) and not source:
            source = context.path
        session = self._get_session(context)
        rcv = session.receiver(name or self._get_id(session.connection.container, source, target))
        if source:
            rcv.source.address = source
        if dynamic:
            rcv.source.dynamic = True
        if target:
            rcv.target.address = target
        if handler:
            rcv.context = handler
        _apply_link_options(options, rcv)
        rcv.open()
        return rcv

    def declare_transaction(self, context, handler=None, settle_before_discharge=False):
        if not _get_attr(context, '_txn_ctrl'):
            context._txn_ctrl = self.create_sender(context, None, name='txn-ctrl')
            context._txn_ctrl.target.type = Terminus.COORDINATOR
            context._txn_ctrl.target.capabilities.put_object(symbol(u'amqp:local-transactions'))
        return Transaction(context._txn_ctrl, handler, settle_before_discharge)

    def listen(self, url):
        host, port = Urls([url]).next()
        return AmqpAcceptor(self.events, self, host, port)

    def schedule(self, deadline, connection=None, session=None, link=None, delivery=None, subject=None):
        self.events.timer.schedule(deadline, ApplicationEvent("timer", connection, session, link, delivery, subject))

    def get_event_trigger(self):
        if not self.trigger or self.trigger.closed():
            self.trigger = EventInjector(self.events.collector)
            self.add(self.trigger)
        return self.trigger

    def add(self, selectable):
        self.loop.add(selectable)

    def remove(self, selectable):
        self.loop.remove(selectable)

    def run(self):
        self.events.dispatch(StartEvent(self))
        self.loop.run()

    def stop(self):
        self.loop.abort()

    def do_work(self, timeout=None):
        return self.loop.do_work(timeout)
