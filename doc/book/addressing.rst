.. Licensed to the Apache Software Foundation (ASF) under one
   or more contributor license agreements.  See the NOTICE file
   distributed with this work for additional information
   regarding copyright ownership.  The ASF licenses this file
   to you under the Apache License, Version 2.0 (the
   "License"); you may not use this file except in compliance
   with the License.  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing,
   software distributed under the License is distributed on an
   "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
   KIND, either express or implied.  See the License for the
   specific language governing permissions and limitations
   under the License.

Addressing
==========

AMQP addresses are used to control the flow of messages across a network
of routers. Addresses are used in a number of different places in the
AMQP 1.0 protocol. They can be used in a specific message in the `to`
and `reply-to` fields of a message's properties. They are also used
during the creation of links in the `address` field of a `source` or
a `target`.

Addresses designate various kinds of entities in a messaging network:

-  Endpoint processes that consume data or offer a service
-  Topics that match multiple consumers to multiple producers
-  Entities within a messaging broker:
   -  Queues
   -  Durable Topics
   -  Exchanges

The syntax of an AMQP address is opaque as far as the router network is
concerned. A syntactical structure may be used by the administrator that
creates addresses, but the router treats them as opaque strings. Routers
consider addresses to be mobile such that any address may be directly
connected to any router in a network and may move around the topology.
In cases where messages are broadcast to or balanced across multiple
consumers, an address may be connected to multiple routers in the
network.

Addresses have semantics associated with them. When an address is
created in the network, it is assigned a set of semantics (and access
rules) during a process called provisioning. The semantics of an address
control how routers behave when they see the address being used.

Address semantics include the following considerations:

-  *Routing pattern* - direct, multicast, balanced
-  *Undeliverable action* - drop, hold and retry, redirect
-  *Reliability* - N destinations, etc.

Routing patterns
----------------

Routing patterns constrain the paths that a message can take across a
network.

+---------------+-------------------------------------------------------------------------+
| *Pattern*     | *Description*                                                           |
+===============+=========================================================================+
| *Direct*      |Direct routing allows for only one consumer to use an address at a       |
|               |time. Messages (or links) follow the lowest cost path across the network |
|               |from the sender to the one receiver.                                     |
+---------------+-------------------------------------------------------------------------+
| *Multicast*   |Multicast routing allows multiple consumers to use the same address at   |
|               |the same time. Messages are routed such that each consumer receives a    |
|               |copy of the message.                                                     |
+---------------+-------------------------------------------------------------------------+
| *Balanced*    |Balanced routing also allows multiple consumers to use the same          |
|               |address. In this case, messages are routed to exactly one of the         |
|               |consumers, and the network attempts to balance the traffic load across   |
|               |the set of consumers using the same address.                             |
+---------------+-------------------------------------------------------------------------+

Routing mechanisms
------------------

The fact that addresses can be used in different ways suggests that
message routing can be accomplished in different ways. Before going into
the specifics of the different routing mechanisms, it would be good to
first define what is meant by the term *routing*:

    In a network built of multiple routers connected by connections
    (i.e., nodes and edges in a graph), *routing* determines which
    connection to use to send a message directly to its destination or
    one step closer to its destination.

Each router serves as the terminus of a collection of incoming and
outgoing links. The links either connect directly to endpoints that
produce and consume messages, or they connect to other routers in the
network along previously established connections.

Message routing
~~~~~~~~~~~~~~~

Message routing occurs upon delivery of a message and is done based on
the address in the message's `to` field.

When a delivery arrives on an incoming link, the router extracts the
address from the delivered message's `to` field and looks the address
up in its routing table. The lookup results in zero or more outgoing
links onto which the message shall be resent.

+-----------------+-----------------------------------------------------------------------+
| *Delivery*      | *Handling*                                                            |
+=================+=======================================================================+
| *pre-settled*   |If the arriving delivery is pre-settled (i.e., fire and forget), the   |
|                 |incoming delivery shall be settled by the router, and the outgoing     |
|                 |deliveries shall also be pre-settled. In other words, the pre-settled  |
|                 |nature of the message delivery is propagated across the network to the |
|                 |message's destination.                                                 |
|                 |                                                                       |
+-----------------+-----------------------------------------------------------------------+
| *unsettled*     |Unsettled delivery is also propagated across the network. Because      |
|                 |unsettled delivery records cannot be discarded, the router tracks the  |
|                 |incoming deliveries and keeps the association of the incoming          |
|                 |deliveries to the resulting outgoing deliveries. This kept association |
|                 |allows the router to continue to propagate changes in delivery state   |
|                 |(settlement and disposition) back and forth along the path which the   |
|                 |message traveled.                                                      |
|                 |                                                                       |
+-----------------+-----------------------------------------------------------------------+
