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

Console installation
====================

Prerequisites
-------------

The following need to be installed before running a console:

- One or more dispatch routers. See the documentation for the dispatch router for help in starting a router network.
- node.js This is needed to provide a proxy between the console's websocket traffic and tcp.
- A web server. This can be any server capable of serving static html/js/css/image files.

A nodejs proxy is distributed with proton.
To start the proton's nodejs proxy::
   cd ~/rh-qpid-proton/examples/javascript/messenger
   node proxy.js &

This will start the proxy listening to ws traffic on port 5673 and translating it to tcp on port 5672.
One of the routers in the network needs to have a listener configured on port 5672. That listener's role should be 'normal'. For example::
   listener {
      addr: 0.0.0.0
      role: normal
      port: amqp
      saslMechanisms: ANONYMOUS
   }


The console files
-----------------

The files for the console are located under the console directory in
the source tree.::
   app/
   bower_components/
   css/
   img/
   index.html
   lib/
   plugin/
   vendor.js

Copy these files to a directory under the the html or webapps directory of your web server. For example, for apache tomcat the files should be under webapps/dispatch. Then the console is available as::
   http://localhost:8080/dispatch

