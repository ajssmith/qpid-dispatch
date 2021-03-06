/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

#include "router_core_private.h"
#include <stdio.h>

static void qdr_add_router_CT        (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_del_router_CT        (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_set_link_CT          (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_remove_link_CT       (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_set_next_hop_CT      (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_remove_next_hop_CT   (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_set_valid_origins_CT (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_map_destination_CT   (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_unmap_destination_CT (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_subscribe_CT         (qdr_core_t *core, qdr_action_t *action, bool discard);
static void qdr_unsubscribe_CT       (qdr_core_t *core, qdr_action_t *action, bool discard);


//==================================================================================
// Interface Functions
//==================================================================================

void qdr_core_add_router(qdr_core_t *core, const char *address, int router_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_add_router_CT, "add_router");
    action->args.route_table.router_maskbit = router_maskbit;
    action->args.route_table.address        = qdr_field(address);
    qdr_action_enqueue(core, action);
}


void qdr_core_del_router(qdr_core_t *core, int router_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_del_router_CT, "del_router");
    action->args.route_table.router_maskbit = router_maskbit;
    qdr_action_enqueue(core, action);
}


void qdr_core_set_link(qdr_core_t *core, int router_maskbit, int link_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_set_link_CT, "set_link");
    action->args.route_table.router_maskbit = router_maskbit;
    action->args.route_table.link_maskbit   = link_maskbit;
    qdr_action_enqueue(core, action);
}


void qdr_core_remove_link(qdr_core_t *core, int router_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_remove_link_CT, "remove_link");
    action->args.route_table.router_maskbit = router_maskbit;
    qdr_action_enqueue(core, action);
}


void qdr_core_set_next_hop(qdr_core_t *core, int router_maskbit, int nh_router_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_set_next_hop_CT, "set_next_hop");
    action->args.route_table.router_maskbit    = router_maskbit;
    action->args.route_table.nh_router_maskbit = nh_router_maskbit;
    qdr_action_enqueue(core, action);
}


void qdr_core_remove_next_hop(qdr_core_t *core, int router_maskbit)
{
    qdr_action_t *action = qdr_action(qdr_remove_next_hop_CT, "remove_next_hop");
    action->args.route_table.router_maskbit = router_maskbit;
    qdr_action_enqueue(core, action);
}


void qdr_core_set_valid_origins(qdr_core_t *core, int router_maskbit, qd_bitmask_t *routers)
{
    qdr_action_t *action = qdr_action(qdr_set_valid_origins_CT, "set_valid_origins");
    action->args.route_table.router_maskbit = router_maskbit;
    action->args.route_table.router_set     = routers;
    qdr_action_enqueue(core, action);
}


void qdr_core_map_destination(qdr_core_t *core, int router_maskbit, const char *address_hash)
{
    qdr_action_t *action = qdr_action(qdr_map_destination_CT, "map_destination");
    action->args.route_table.router_maskbit = router_maskbit;
    action->args.route_table.address        = qdr_field(address_hash);
    qdr_action_enqueue(core, action);
}


void qdr_core_unmap_destination(qdr_core_t *core, int router_maskbit, const char *address_hash)
{
    qdr_action_t *action = qdr_action(qdr_unmap_destination_CT, "unmap_destination");
    action->args.route_table.router_maskbit = router_maskbit;
    action->args.route_table.address        = qdr_field(address_hash);
    qdr_action_enqueue(core, action);
}

void qdr_core_route_table_handlers(qdr_core_t           *core, 
                                   void                 *context,
                                   qdr_mobile_added_t    mobile_added,
                                   qdr_mobile_removed_t  mobile_removed,
                                   qdr_link_lost_t       link_lost)
{
    core->rt_context        = context;
    core->rt_mobile_added   = mobile_added;
    core->rt_mobile_removed = mobile_removed;
    core->rt_link_lost      = link_lost;
}


qdr_subscription_t *qdr_core_subscribe(qdr_core_t             *core,
                                       const char             *address,
                                       char                    aclass,
                                       char                    phase,
                                       qd_address_treatment_t  treatment,
                                       qdr_receive_t           on_message,
                                       void                   *context)
{
    qdr_subscription_t *sub = NEW(qdr_subscription_t);
    sub->core               = core;
    sub->addr               = 0;
    sub->on_message         = on_message;
    sub->on_message_context = context;

    qdr_action_t *action = qdr_action(qdr_subscribe_CT, "subscribe");
    action->args.io.address       = qdr_field(address);
    action->args.io.address_class = aclass;
    action->args.io.address_phase = phase;
    action->args.io.subscription  = sub;
    action->args.io.treatment     = treatment;
    qdr_action_enqueue(core, action);

    return sub;
}


void qdr_core_unsubscribe(qdr_subscription_t *sub)
{
    if (sub) {
        qdr_action_t *action = qdr_action(qdr_unsubscribe_CT, "unsubscribe");
        action->args.io.subscription = sub;
        qdr_action_enqueue(sub->core, action);
    }
}


//==================================================================================
// In-Thread Functions
//==================================================================================

void qdr_route_table_setup_CT(qdr_core_t *core)
{
    DEQ_INIT(core->addrs);
    DEQ_INIT(core->routers);
    core->addr_hash    = qd_hash(12, 32, 0);
    core->conn_id_hash = qd_hash(6, 4, 0);

    if (core->router_mode == QD_ROUTER_MODE_INTERIOR) {
        core->hello_addr      = qdr_add_local_address_CT(core, 'L', "qdhello",     QD_TREATMENT_MULTICAST_FLOOD);
        core->router_addr_L   = qdr_add_local_address_CT(core, 'L', "qdrouter",    QD_TREATMENT_MULTICAST_FLOOD);
        core->routerma_addr_L = qdr_add_local_address_CT(core, 'L', "qdrouter.ma", QD_TREATMENT_MULTICAST_ONCE);
        core->router_addr_T   = qdr_add_local_address_CT(core, 'T', "qdrouter",    QD_TREATMENT_MULTICAST_FLOOD);
        core->routerma_addr_T = qdr_add_local_address_CT(core, 'T', "qdrouter.ma", QD_TREATMENT_MULTICAST_ONCE);

        core->neighbor_free_mask = qd_bitmask(1);

        core->routers_by_mask_bit       = NEW_PTR_ARRAY(qdr_node_t, qd_bitmask_width());
        core->control_links_by_mask_bit = NEW_PTR_ARRAY(qdr_link_t, qd_bitmask_width());
        core->data_links_by_mask_bit    = NEW_PTR_ARRAY(qdr_link_t, qd_bitmask_width());
        for (int idx = 0; idx < qd_bitmask_width(); idx++) {
            core->routers_by_mask_bit[idx]   = 0;
            core->control_links_by_mask_bit[idx] = 0;
            core->data_links_by_mask_bit[idx] = 0;
        }
    }
}


static void qdr_add_router_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int          router_maskbit = action->args.route_table.router_maskbit;
    qdr_field_t *address        = action->args.route_table.address;

    if (discard) {
        qdr_field_free(address);
        return;
    }

    do {
        if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "add_router: Router maskbit out of range: %d", router_maskbit);
            break;
        }

        if (core->routers_by_mask_bit[router_maskbit] != 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "add_router: Router maskbit already in use: %d", router_maskbit);
            break;
        }

        //
        // Hash lookup the address to ensure there isn't an existing router address.
        //
        qd_field_iterator_t *iter = address->iterator;
        qdr_address_t       *addr;

        qd_address_iterator_reset_view(iter, ITER_VIEW_ADDRESS_HASH);
        qd_hash_retrieve(core->addr_hash, iter, (void**) &addr);

        if (addr) {
            qd_log(core->log, QD_LOG_CRITICAL, "add_router: Data inconsistency for router-maskbit %d", router_maskbit);
            assert(addr == 0);  // Crash in debug mode.  This should never happen
            break;
        }

        //
        // Create an address record for this router and insert it in the hash table.
        // This record will be found whenever a "foreign" topological address to this
        // remote router is looked up.
        //
        addr = qdr_address_CT(core, QD_TREATMENT_ANYCAST_CLOSEST);
        qd_hash_insert(core->addr_hash, iter, addr, &addr->hash_handle);
        DEQ_INSERT_TAIL(core->addrs, addr);

        //
        // Create a router-node record to represent the remote router.
        //
        qdr_node_t *rnode = new_qdr_node_t();
        DEQ_ITEM_INIT(rnode);
        rnode->owning_addr       = addr;
        rnode->mask_bit          = router_maskbit;
        rnode->next_hop          = 0;
        rnode->peer_control_link = 0;
        rnode->peer_data_link    = 0;
        rnode->ref_count         = 0;
        rnode->valid_origins     = qd_bitmask(0);

        DEQ_INSERT_TAIL(core->routers, rnode);

        //
        // Link the router record to the address record.
        //
        qd_bitmask_set_bit(addr->rnodes, router_maskbit);

        //
        // Link the router record to the router address records.
        // Use the T-class addresses only.
        //
        qd_bitmask_set_bit(core->router_addr_T->rnodes, router_maskbit);
        qd_bitmask_set_bit(core->routerma_addr_T->rnodes, router_maskbit);

        //
        // Bump the ref-count by three for each of the above links.
        //
        rnode->ref_count += 3;

        //
        // Add the router record to the mask-bit index.
        //
        core->routers_by_mask_bit[router_maskbit] = rnode;
    } while (false);

    qdr_field_free(address);
}


static void qdr_del_router_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int router_maskbit = action->args.route_table.router_maskbit;

    if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "del_router: Router maskbit out of range: %d", router_maskbit);
        return;
    }

    if (core->routers_by_mask_bit[router_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "del_router: Deleting nonexistent router: %d", router_maskbit);
        return;
    }

    qdr_node_t    *rnode = core->routers_by_mask_bit[router_maskbit];
    qdr_address_t *oaddr = rnode->owning_addr;
    assert(oaddr);

    //
    // Unlink the router node from the address record
    //
    qd_bitmask_clear_bit(oaddr->rnodes, router_maskbit);
    qd_bitmask_clear_bit(core->router_addr_T->rnodes, router_maskbit);
    qd_bitmask_clear_bit(core->routerma_addr_T->rnodes, router_maskbit);
    rnode->ref_count -= 3;

    //
    // While the router node has a non-zero reference count, look for addresses
    // to unlink the node from.
    //
    qdr_address_t *addr = DEQ_HEAD(core->addrs);
    while (addr && rnode->ref_count > 0) {
        if (qd_bitmask_clear_bit(addr->rnodes, router_maskbit))
            //
            // If the cleared bit was originally set, decrement the ref count
            //
            rnode->ref_count--;
        addr = DEQ_NEXT(addr);
    }
    assert(rnode->ref_count == 0);

    //
    // Free the router node and the owning address records.
    //
    qd_bitmask_free(rnode->valid_origins);
    DEQ_REMOVE(core->routers, rnode);
    free_qdr_node_t(rnode);

    qd_hash_remove_by_handle(core->addr_hash, oaddr->hash_handle);
    DEQ_REMOVE(core->addrs, oaddr);
    qd_hash_handle_free(oaddr->hash_handle);
    core->routers_by_mask_bit[router_maskbit] = 0;
    free_qdr_address_t(oaddr);
}


static void qdr_set_link_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int router_maskbit = action->args.route_table.router_maskbit;
    int link_maskbit   = action->args.route_table.link_maskbit;

    if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_link: Router maskbit out of range: %d", router_maskbit);
        return;
    }

    if (link_maskbit >= qd_bitmask_width() || link_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_link: Link maskbit out of range: %d", link_maskbit);
        return;
    }

    if (core->control_links_by_mask_bit[link_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_link: Invalid link reference: %d", link_maskbit);
        return;
    }

    if (core->routers_by_mask_bit[router_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_link: Router not found");
        return;
    }

    //
    // Add the peer_link reference to the router record.
    //
    qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
    rnode->peer_control_link = core->control_links_by_mask_bit[link_maskbit];
    rnode->peer_data_link    = core->data_links_by_mask_bit[link_maskbit];
}


static void qdr_remove_link_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int router_maskbit = action->args.route_table.router_maskbit;

    if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "remove_link: Router maskbit out of range: %d", router_maskbit);
        return;
    }

    if (core->routers_by_mask_bit[router_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "remove_link: Router not found");
        return;
    }

    qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
    rnode->peer_control_link = 0;
    rnode->peer_data_link    = 0;
}


static void qdr_set_next_hop_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int router_maskbit    = action->args.route_table.router_maskbit;
    int nh_router_maskbit = action->args.route_table.nh_router_maskbit;

    if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_next_hop: Router maskbit out of range: %d", router_maskbit);
        return;
    }

    if (nh_router_maskbit >= qd_bitmask_width() || nh_router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_next_hop: Next hop router maskbit out of range: %d", router_maskbit);
        return;
    }

    if (core->routers_by_mask_bit[router_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_next_hop: Router not found");
        return;
    }

    if (core->routers_by_mask_bit[nh_router_maskbit] == 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "set_next_hop: Next hop router not found");
        return;
    }

    if (router_maskbit != nh_router_maskbit) {
        qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
        rnode->next_hop   = core->routers_by_mask_bit[nh_router_maskbit];
    }
}


static void qdr_remove_next_hop_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int router_maskbit = action->args.route_table.router_maskbit;

    if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
        qd_log(core->log, QD_LOG_CRITICAL, "remove_next_hop: Router maskbit out of range: %d", router_maskbit);
        return;
    }

    qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
    rnode->next_hop = 0;
}


static void qdr_set_valid_origins_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int           router_maskbit = action->args.route_table.router_maskbit;
    qd_bitmask_t *valid_origins  = action->args.route_table.router_set;

    if (discard) {
        qd_bitmask_free(valid_origins);
        return;
    }

    do {
        if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "set_valid_origins: Router maskbit out of range: %d", router_maskbit);
            break;
        }

        if (core->routers_by_mask_bit[router_maskbit] == 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "set_valid_origins: Router not found");
            break;
        }

        qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
        if (rnode->valid_origins)
            qd_bitmask_free(rnode->valid_origins);
        rnode->valid_origins = valid_origins;
        valid_origins = 0;
    } while (false);

    if (valid_origins)
        qd_bitmask_free(valid_origins);
}


static void qdr_map_destination_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    //
    // TODO - handle the class-prefix and phase explicitly
    //

    int          router_maskbit = action->args.route_table.router_maskbit;
    qdr_field_t *address        = action->args.route_table.address;

    if (discard) {
        qdr_field_free(address);
        return;
    }

    do {
        if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "map_destination: Router maskbit out of range: %d", router_maskbit);
            break;
        }

        if (core->routers_by_mask_bit[router_maskbit] == 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "map_destination: Router not found");
            break;
        }

        qd_field_iterator_t *iter = address->iterator;
        qdr_address_t       *addr = 0;

        qd_hash_retrieve(core->addr_hash, iter, (void**) &addr);
        if (!addr) {
            addr = qdr_address_CT(core, qdr_treatment_for_address_hash_CT(core, iter));
            qd_hash_insert(core->addr_hash, iter, addr, &addr->hash_handle);
            DEQ_ITEM_INIT(addr);
            DEQ_INSERT_TAIL(core->addrs, addr);
        }

        qdr_node_t *rnode = core->routers_by_mask_bit[router_maskbit];
        qd_bitmask_set_bit(addr->rnodes, router_maskbit);
        rnode->ref_count++;
        qdr_addr_start_inlinks_CT(core, addr);

        //
        // TODO - If this affects a waypoint, create the proper side effects
        //
    } while (false);

    qdr_field_free(address);
}


static void qdr_unmap_destination_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    int          router_maskbit = action->args.route_table.router_maskbit;
    qdr_field_t *address        = action->args.route_table.address;

    if (discard) {
        qdr_field_free(address);
        return;
    }

    do {
        if (router_maskbit >= qd_bitmask_width() || router_maskbit < 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "unmap_destination: Router maskbit out of range: %d", router_maskbit);
            break;
        }

        if (core->routers_by_mask_bit[router_maskbit] == 0) {
            qd_log(core->log, QD_LOG_CRITICAL, "unmap_destination: Router not found");
            break;
        }

        qdr_node_t          *rnode = core->routers_by_mask_bit[router_maskbit];
        qd_field_iterator_t *iter  = address->iterator;
        qdr_address_t       *addr  = 0;

        qd_hash_retrieve(core->addr_hash, iter, (void**) &addr);

        if (!addr) {
            qd_log(core->log, QD_LOG_CRITICAL, "unmap_destination: Address not found");
            break;
        }

        qd_bitmask_clear_bit(addr->rnodes, router_maskbit);
        rnode->ref_count--;

        //
        // TODO - If this affects a waypoint, create the proper side effects
        //

        qdr_check_addr_CT(core, addr, false);
    } while (false);

    qdr_field_free(address);
}


static void qdr_subscribe_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    qdr_field_t        *address = action->args.io.address;
    qdr_subscription_t *sub     = action->args.io.subscription;

    if (!discard) {
        char aclass         = action->args.io.address_class;
        char phase          = action->args.io.address_phase;
        qdr_address_t *addr = 0;

        char *astring = (char*) qd_field_iterator_copy(address->iterator);
        qd_log(core->log, QD_LOG_INFO, "In-process subscription %c/%s", aclass, astring);
        free(astring);

        qd_address_iterator_override_prefix(address->iterator, aclass);
        if (aclass == 'M')
            qd_address_iterator_set_phase(address->iterator, phase);
        qd_address_iterator_reset_view(address->iterator, ITER_VIEW_ADDRESS_HASH);

        qd_hash_retrieve(core->addr_hash, address->iterator, (void**) &addr);
        if (!addr) {
            addr = qdr_address_CT(core, action->args.io.treatment);
            qd_hash_insert(core->addr_hash, address->iterator, addr, &addr->hash_handle);
            DEQ_ITEM_INIT(addr);
            DEQ_INSERT_TAIL(core->addrs, addr);
        }

        sub->addr = addr;
        DEQ_ITEM_INIT(sub);
        DEQ_INSERT_TAIL(addr->subscriptions, sub);
        qdr_addr_start_inlinks_CT(core, addr);

    } else
        free(sub);

    qdr_field_free(address);
}


static void qdr_unsubscribe_CT(qdr_core_t *core, qdr_action_t *action, bool discard)
{
    qdr_subscription_t *sub = action->args.io.subscription;

    if (!discard) {
        DEQ_REMOVE(sub->addr->subscriptions, sub);
        sub->addr = 0;
        qdr_check_addr_CT(sub->core, sub->addr, false);
    }

    free(sub);
}

//==================================================================================
// Call-back Functions
//==================================================================================

static void qdr_do_mobile_added(qdr_core_t *core, qdr_general_work_t *work)
{
    char *address_hash = qdr_field_copy(work->field);
    if (address_hash) {
        core->rt_mobile_added(core->rt_context, address_hash);
        free(address_hash);
    }

    qdr_field_free(work->field);
}


static void qdr_do_mobile_removed(qdr_core_t *core, qdr_general_work_t *work)
{
    char *address_hash = qdr_field_copy(work->field);
    if (address_hash) {
        core->rt_mobile_removed(core->rt_context, address_hash);
        free(address_hash);
    }

    qdr_field_free(work->field);
}


static void qdr_do_link_lost(qdr_core_t *core, qdr_general_work_t *work)
{
    core->rt_link_lost(core->rt_context, work->maskbit);
}


void qdr_post_mobile_added_CT(qdr_core_t *core, const char *address_hash)
{
    qdr_general_work_t *work = qdr_general_work(qdr_do_mobile_added);
    work->field = qdr_field(address_hash);
    qdr_post_general_work_CT(core, work);
}


void qdr_post_mobile_removed_CT(qdr_core_t *core, const char *address_hash)
{
    qdr_general_work_t *work = qdr_general_work(qdr_do_mobile_removed);
    work->field = qdr_field(address_hash);
    qdr_post_general_work_CT(core, work);
}


void qdr_post_link_lost_CT(qdr_core_t *core, int link_maskbit)
{
    qdr_general_work_t *work = qdr_general_work(qdr_do_link_lost);
    work->maskbit = link_maskbit;
    qdr_post_general_work_CT(core, work);
}


