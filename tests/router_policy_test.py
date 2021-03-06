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

import unittest

from qpid_dispatch_internal.policy.policy_util import HostAddr
from qpid_dispatch_internal.policy.policy_util import HostStruct
from qpid_dispatch_internal.policy.policy_util import PolicyError
from qpid_dispatch_internal.policy.policy_util import PolicyAppConnectionMgr
from qpid_dispatch_internal.policy.policy_local import PolicyLocal
from system_test import TestCase, main_module

class PolicyHostAddrTest(TestCase):

    def expect_deny(self, badhostname, msg):
        denied = False
        try:
            xxx = HostStruct(badhostname)
        except PolicyError:
            denied = True
        self.assertTrue(denied, ("%s" % msg))

    def check_hostaddr_match(self, tHostAddr, tString, expectOk=True):
        # check that the string is a match for the addr
        # check that the internal struct version matches, too
        ha = HostStruct(tString)
        if expectOk:
            self.assertTrue( tHostAddr.match_str(tString) )
            self.assertTrue( tHostAddr.match_bin(ha) )
        else:
            self.assertFalse( tHostAddr.match_str(tString) )
            self.assertFalse( tHostAddr.match_bin(ha) )

    def test_policy_hostaddr_ipv4(self):
        # Create simple host and range
        aaa = HostAddr("192.168.1.1")
        bbb = HostAddr("1.1.1.1,1.1.1.255")
        # Verify host and range
        self.check_hostaddr_match(aaa, "192.168.1.1")
        self.check_hostaddr_match(aaa, "1.1.1.1", False)
        self.check_hostaddr_match(aaa, "192.168.1.2", False)
        self.check_hostaddr_match(bbb, "1.1.1.1")
        self.check_hostaddr_match(bbb, "1.1.1.254")
        self.check_hostaddr_match(bbb, "1.1.1.0", False)
        self.check_hostaddr_match(bbb, "1.1.2.0", False)

    def test_policy_hostaddr_ipv6(self):
        if not HostAddr.has_ipv6:
            self.skipTest("System IPv6 support is not available")
        # Create simple host and range
        aaa = HostAddr("::1")
        bbb = HostAddr("::1,::ffff")
        ccc = HostAddr("ffff::0,ffff:ffff::0")
        # Verify host and range
        self.check_hostaddr_match(aaa, "::1")
        self.check_hostaddr_match(aaa, "::2", False)
        self.check_hostaddr_match(aaa, "ffff:ffff::0", False)
        self.check_hostaddr_match(bbb, "::1")
        self.check_hostaddr_match(bbb, "::fffe")
        self.check_hostaddr_match(bbb, "::1:0", False)
        self.check_hostaddr_match(bbb, "ffff::0", False)
        self.check_hostaddr_match(ccc, "ffff::1")
        self.check_hostaddr_match(ccc, "ffff:fffe:ffff:ffff::ffff")
        self.check_hostaddr_match(ccc, "ffff:ffff::1", False)
        self.check_hostaddr_match(ccc, "ffff:ffff:ffff:ffff::ffff", False)

    def test_policy_hostaddr_ipv4_wildcard(self):
        aaa = HostAddr("*")
        self.check_hostaddr_match(aaa,"0.0.0.0")
        self.check_hostaddr_match(aaa,"127.0.0.1")
        self.check_hostaddr_match(aaa,"255.254.253.252")


    def test_policy_hostaddr_ipv6_wildcard(self):
        if not HostAddr.has_ipv6:
            self.skipTest("System IPv6 support is not available")
        aaa = HostAddr("*")
        self.check_hostaddr_match(aaa,"::0")
        self.check_hostaddr_match(aaa,"::1")
        self.check_hostaddr_match(aaa,"ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff")

    def test_policy_malformed_hostaddr_ipv4(self):
        self.expect_deny( "0.0.0.0.0", "Name or service not known")
        self.expect_deny( "1.1.1.1,2.2.2.2,3.3.3.3", "arg count")
        self.expect_deny( "9.9.9.9,8.8.8.8", "a > b")

    def test_policy_malformed_hostaddr_ipv6(self):
        if not HostAddr.has_ipv6:
            self.skipTest("System IPv6 support is not available")
        self.expect_deny( "1::2::3", "Name or service not known")
        self.expect_deny( "::1,::2,::3", "arg count")
        self.expect_deny( "0:ff:0,0:fe:ffff:ffff::0", "a > b")

class QpidDispatch(object):
    def qd_dispatch_policy_c_counts_alloc(self):
        return 100

    def qd_dispatch_policy_c_counts_refresh(self, cstats, entitymap):
        pass

class MockAgent(object):
    def __init__(self):
        self.qd = QpidDispatch()

    def add_implementation(self, entity, cfg_obj_name):
        pass

class MockPolicyManager(object):
    def __init__(self):
        self.agent = MockAgent()

    def log_debug(self, text):
        print("DEBUG: %s" % text)
    def log_info(self, text):
        print("INFO: %s" % text)
    def log_trace(self, text):
        print("TRACE: %s" % text)
    def log_error(self, text):
        print("ERROR: %s" % text)

    def get_agent(self):
        return self.agent

class PolicyFile(TestCase):

    manager = MockPolicyManager()
    policy = PolicyLocal(manager)
    policy.test_load_config()

    def test_policy1_test_zeke_ok(self):
        p1 = PolicyFile.policy.lookup_user('zeke', '192.168.100.5', 'photoserver', '192.168.100.5:33333', 1)
        self.assertTrue(p1 == 'test')
        upolicy = {}
        self.assertTrue(
            PolicyFile.policy.lookup_settings('photoserver', p1, upolicy)
        )
        self.assertTrue(upolicy['maxFrameSize']            == 444444)
        self.assertTrue(upolicy['maxMessageSize']          == 444444)
        self.assertTrue(upolicy['maxSessionWindow']        == 444444)
        self.assertTrue(upolicy['maxSessions']              == 4)
        self.assertTrue(upolicy['maxSenders']               == 44)
        self.assertTrue(upolicy['maxReceivers']             == 44)
        self.assertTrue(upolicy['allowAnonymousSender'])
        self.assertTrue(upolicy['allowDynamicSrc'])
        self.assertTrue(upolicy['targets'] == 'private')
        self.assertTrue(upolicy['sources'] == 'private')

    def test_policy1_test_zeke_bad_IP(self):
        self.assertTrue(
            PolicyFile.policy.lookup_user('zeke', '10.18.0.1',    'photoserver', "connid", 2) == '')
        self.assertTrue(
            PolicyFile.policy.lookup_user('zeke', '72.135.2.9',   'photoserver', "connid", 3) == '')
        self.assertTrue(
            PolicyFile.policy.lookup_user('zeke', '127.0.0.1',    'photoserver', "connid", 4) == '')

    def test_policy1_test_zeke_bad_app(self):
        self.assertTrue(
            PolicyFile.policy.lookup_user('zeke', '192.168.100.5','galleria', "connid", 5) == '')

    def test_policy1_test_users_same_permissions(self):
        zname = PolicyFile.policy.lookup_user('zeke', '192.168.100.5', 'photoserver', '192.168.100.5:33333', 6)
        yname = PolicyFile.policy.lookup_user('ynot', '10.48.255.254', 'photoserver', '192.168.100.5:33334', 7)
        self.assertTrue( zname == yname )

    def test_policy1_lookup_unknown_application(self):
        upolicy = {}
        self.assertFalse(
            PolicyFile.policy.lookup_settings('unknown', 'doesntmatter', upolicy)
        )

    def test_policy1_lookup_unknown_usergroup(self):
        upolicy = {}
        self.assertFalse(
            PolicyFile.policy.lookup_settings('photoserver', 'unknown', upolicy)
        )

class PolicyAppConnectionMgrTests(TestCase):

    def test_policy_app_conn_mgr_fail_by_total(self):
        stats = PolicyAppConnectionMgr(1, 2, 2)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 1)
        self.assertTrue('application connection limit' in diags[0])

    def test_policy_app_conn_mgr_fail_by_user(self):
        stats = PolicyAppConnectionMgr(3, 1, 2)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 1)
        self.assertTrue('per user' in diags[0])

    def test_policy_app_conn_mgr_fail_by_hosts(self):
        stats = PolicyAppConnectionMgr(3, 2, 1)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 1)
        self.assertTrue('per host' in diags[0])

    def test_policy_app_conn_mgr_fail_by_user_hosts(self):
        stats = PolicyAppConnectionMgr(3, 1, 1)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 2)
        self.assertTrue('per user' in diags[0] or 'per user' in diags[1])
        self.assertTrue('per host' in diags[0] or 'per host' in diags[1])

    def test_policy_app_conn_mgr_update(self):
        stats = PolicyAppConnectionMgr(3, 1, 2)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 1)
        self.assertTrue('per user' in diags[0])
        diags = []
        stats.update(3, 2, 2)
        self.assertTrue(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))

    def test_policy_app_conn_mgr_disconnect(self):
        stats = PolicyAppConnectionMgr(3, 1, 2)
        diags = []
        self.assertTrue(stats.can_connect('10.10.10.10:10000', 'chuck', '10.10.10.10', diags))
        self.assertFalse(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))
        self.assertTrue(len(diags) == 1)
        self.assertTrue('per user' in diags[0])
        diags = []
        stats.disconnect("10.10.10.10:10000", 'chuck', '10.10.10.10')
        self.assertTrue(stats.can_connect('10.10.10.10:10001', 'chuck', '10.10.10.10', diags))

    def test_policy_app_conn_mgr_create_bad_settings(self):
        denied = False
        try:
            stats = PolicyAppConnectionMgr(-3, 1, 2)
        except PolicyError:
            denied = True
        self.assertTrue(denied, "Failed to detect negative setting value.")

    def test_policy_app_conn_mgr_update_bad_settings(self):
        denied = False
        try:
            stats = PolicyAppConnectionMgr(0, 0, 0)
        except PolicyError:
            denied = True
        self.assertFalse(denied, "Should allow all zeros.")
        try:
            stats.update(0, -1, 0)
        except PolicyError:
            denied = True
        self.assertTrue(denied, "Failed to detect negative setting value.")

    def test_policy_app_conn_mgr_larger_counts(self):
        stats = PolicyAppConnectionMgr(10000, 10000, 10000)
        diags = []
        for i in range(0, 10000):
            self.assertTrue(stats.can_connect('1.1.1.1:' + str(i), 'chuck', '1.1.1.1', diags))
            self.assertTrue(len(diags) == 0)
        self.assertFalse(stats.can_connect('1.1.1.1:10000', 'chuck', '1.1.1.1', diags))
        self.assertTrue(len(diags) == 3)
        self.assertTrue(stats.connections_active == 10000)
        self.assertTrue(stats.connections_approved == 10000)
        self.assertTrue(stats.connections_denied == 1)

if __name__ == '__main__':
    unittest.main(main_module())
