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

AMQP Mapping
============

Dispatch Router is an AMQP router and as such, it provides extensions,
code-points, and semantics for routing over AMQP. This page documents the
details of Dispatch Router's use of AMQP.

Message Annotations
-------------------

The following Message Annotation fields are defined by Dispatch Router:

+--------------------+------------------+-------------------------------------------------------+
| *Field*            | *Type*           | *Description*                                         |
+====================+==================+=======================================================+
| x-opt-qd.ingress   | string           |The identity of the ingress router for a message-routed|
|                    |                  |message. The ingress router is the first router        |
|                    |                  |encountered by a transiting message. The router will,  |
|                    |                  |if this field is present, leave it unaltered. If the   |
|                    |                  |field is not present, the router shall insert the field|
|                    |                  |with its own identity.                                 |
|                    |                  |                                                       |
|                    |                  |                                                       |
|                    |                  |                                                       |
+--------------------+------------------+-------------------------------------------------------+
| x-opt-qd.trace     | list of string   |The list of routers through which this message-routed  |
|                    |                  |message has transited. If this field is not present,   |
|                    |                  |the router shall do nothing. If the field is present,  |
|                    |                  |the router shall append its own identity to the end of |
|                    |                  |the list.                                              |
|                    |                  |                                                       |
|                    |                  |                                                       |
+--------------------+------------------+-------------------------------------------------------+
| x-opt-qd.to        | string           |To-Override for message-routed messages. If this field |
|                    |                  |is present, the address in this field shall be used for|
|                    |                  |routing in lieu of the *to* field in the message       |
|                    |                  |properties. A router may append, remove, or modify this|
|                    |                  |annotation field depending on the policy in place for  |
|                    |                  |routing the message.                                   |
|                    |                  |                                                       |
|                    |                  |                                                       |
|                    |                  |                                                       |
+--------------------+------------------+-------------------------------------------------------+
| x-opt-qd.phase     | integer          |The address-phase, if not zero, for messages flowing   |
|                    |                  |between routers.                                       |
|                    |                  |                                                       |
+--------------------+------------------+-------------------------------------------------------+

Source/Target Capabilities
--------------------------

The following Capability values are used in Sources and Targets.

+----------------+----------------------------------------------------------------------------+
| *Capability*   | *Description*                                                              |
+================+============================================================================+
| qd.router      |This capability is added to sources and targets that are used for           |
|                |inter-router message exchange.  This capability denotes a link used for     |
|                |router-control messages flowing between routers.                            |
+----------------+----------------------------------------------------------------------------+
| qd.router-data |This capability is added to sources and targets that are used for           |
|                |inter-router message exchange.  This capability denotes a link used for     |
|                |user messages being message-routed across an inter-router connection.       |
+----------------+----------------------------------------------------------------------------+

Dynamic-Node-Properties
-----------------------

The following dynamic-node-properties are used by Dispatch in Sources.

+--------------------+-----------------------------------------------------------------------+
| *Property*         | *Description*                                                         |
+====================+=======================================================================+
| x-opt-qd.address   |The node address describing the destination desired for a dynamic      |
|                    |source. If this is absent, the router will terminate any dynamic       |
|                    |receivers. If this address is present, the router will use the address |
|                    |to route the dynamic link attach to the proper destination container.  |
|                    |                                                                       |
+--------------------+-----------------------------------------------------------------------+

Addresses and Address Formats
-----------------------------

The following AMQP addresses and address patterns are used within
Dispatch Router.

Address Patterns
~~~~~~~~~~~~~~~~

+--------------------------------+-------------------------------------------------------+
| *Pattern*                      | *Description*                                         |
+================================+=======================================================+
| `_local/<addr>`                |An address that references a locally attached          |
|                                |endpoint. Messages using this address pattern shall not|
|                                |be routed over more than one link.                     |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
+--------------------------------+-------------------------------------------------------+
| `_topo/0/<router>/<addr>`      |An address that references an endpoint attached to a   |
|                                |specific router node in the network topology. Messages |
|                                |with addresses that follow this pattern shall be routed|
|                                |along the shortest path to the specified router. Note  |
|                                |that addresses of this form are a-priori routable in   |
|                                |that the address itself contains enough information to |
|                                |route the message to its destination.                  |
|                                |                                                       |
|                                |The '0' component immediately preceding the router-id  |
|                                |is a placeholder for an _area_ which may be used in    |
|                                |the future if area routing is implemented.             |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
+--------------------------------+-------------------------------------------------------+
| `<addr>`                       |A mobile address. An address of this format represents |
|                                |an endpoint or a set of distinct endpoints that are    |
|                                |attached to the network in arbitrary locations. It is  |
|                                |the responsibility of the router network to determine  |
|                                |which router nodes are valid destinations for mobile   |
|                                |addresses.                                             |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
|                                |                                                       |
+--------------------------------+-------------------------------------------------------+

Supported Addresses
~~~~~~~~~~~~~~~~~~~

+---------------------------------+------------------------------------------------------------+
| *Address*                       | *Description*                                              |
+=================================+============================================================+
| `$management`                   |The management agent on the attached router/container. This |
|                                 |address would be used by an endpoint that is a management   |
|                                 |client/console/tool wishing to access management data from  |
|                                 |the attached container.                                     |
+---------------------------------+------------------------------------------------------------+
| `_topo/0/Router.E/$management`  |The management agent at Router.E in area 0. This address    |
|                                 |would be used by a management client wishing to access      |
|                                 |management data from a specific container that is reachable |
|                                 |within the network.                                         |
+---------------------------------+------------------------------------------------------------+
| `_local/qdhello`                |The router entity in each of the connected routers. This    |
|                                 |address is used to communicate with neighbor routers and is |
|                                 |exclusively for the HELLO discovery protocol.               |
+---------------------------------+------------------------------------------------------------+
| `_local/qdrouter`               |The router entity in each of the connected routers. This    |
|                                 |address is used by a router to communicate with other       |
|                                 |routers in the network.                                     |
+---------------------------------+------------------------------------------------------------+
| `_topo/0/Router.E/qdrouter`     |The router entity at the specifically indicated router. This|
|                                 |address form is used by a router to communicate with a      |
|                                 |specific router that may or may not be a neighbor.          |
+---------------------------------+------------------------------------------------------------+

Implementation of the AMQP Management Specification
---------------------------------------------------

Qpid Dispatch is manageable remotely via AMQP. It is compliant with the
emerging AMQP Management specification (draft 9).

Differences from the specification:

-  The `name` attribute is not required when an entity is created. If
   not supplied it will be set to the same value as the system-generated
   "identity" attribute. Otherwise it is treated as per the standard.
-  The `REGISTER` and `DEREGISTER` operations are not implemented. The router
   automatically discovers peer routers via the router network and makes
   their management addresses available via the standard GET-MGMT-NODES
   operation.
