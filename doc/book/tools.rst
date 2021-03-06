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

Tools
=====

qdstat
------

*qdstat* is a command line tool that lets you view the status of a
Dispatch Router. The following options are useful for seeing what the
router is doing:

+--------------+-----------------------------------------------------------------------------+
| *Option*     | *Description*                                                               |
+==============+=============================================================================+
| -l           |Print a list of AMQP links attached to the router. Links are                 |
|              |unidirectional. Outgoing links are usually associated with a subscription    |
|              |address. The tool distinguishes between *endpoint* links and *router*        |
|              |links. Endpoint links are attached to clients using the router. Router links |
|              |are attached to other routers in a network of routbers.                      |
|              |                                                                             |
+--------------+-----------------------------------------------------------------------------+
| -a           |Print a list of addresses known to the router.                               |
+--------------+-----------------------------------------------------------------------------+
| -n           |Print a list of known routers in the network.                                |
+--------------+-----------------------------------------------------------------------------+
| -c           |Print a list of connections to the router.                                   |
+--------------+-----------------------------------------------------------------------------+
| --autolinks  |Print a list of configured auto-links.                                       |
+--------------+-----------------------------------------------------------------------------+
| --linkroutes |Print a list of configures link-routes.                                      |
+--------------+-----------------------------------------------------------------------------+

For complete details see the `qdstat(8)` man page and the output of
`qdstat --help`.

qdmanage
--------

*qdmanage* is a general-purpose AMQP management client that allows you
to not only view but modify the configuration of a running dispatch
router.

For example you can query all the connection entities in the router::

   $ qdmanage query --type connection

To enable logging debug and higher level messages by default::

   $ qdmanage update log/DEFAULT enable=debug+

In fact, everything that can be configured in the configuration file can
also be created in a running router via management. For example to
create a new listener in a running router::

   $ qdmanage create type=listener port=5555

Now you can connect to port 5555, for exampple::

   $ qdmanage query -b localhost:5555 --type listener

For complete details see the `qdmanage(8)` man page and the output of
`qdmanage --help`. Also for details of what can be configured see the
`qdrouterd.conf(5)` man page.
