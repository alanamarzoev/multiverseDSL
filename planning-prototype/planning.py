import dataflow
import sys
from dataflow import * 

PERSON_ID_COLS = {'contactID'}

def check_commutativity(op1, op2): 
    print('commutativity check: {} vs {}'.format(op1, op2))
    if type(op1) == Filter and type(op2) == Filter: 
        return True 
    elif type(op1) == Aggregate and type(op2) == Filter:
        return False
    elif type(op1) == Transform and type(op2) == Filter: 
        transform_preds = op1.predicates 
        filter_preds = op2.predicate 

        if '.' in transform_preds: 
            table_transform, col_transform = transform_preds.split(".")
        else: 
            col_transform = None 

        if '.' in filter_preds: 
            table_filter, col_filter = filter_preds.split(".")
        else: 
            col_filter = None
        
        if '.' in transform_preds and '.' in filter_preds and col_transform == col_filter: 
            return False
        elif ('UID' in transform_preds or 'UID' in filter_preds) and (col_filter in PERSON_ID_COLS or col_transform in PERSON_ID_COLS): 
            return False 
        else: 
            return True 
        
    elif type(op1) == Filter and type(op2) == Aggregate: 
        return False 
    elif type(op1) == Aggregate and type(op2) == Aggregate: 
        return False 
        # TODO fill this in 
    elif (type(op1) == Transform and type(op2) == Aggregate) or (type(op1) == Aggregate and type(op2) == Transform): 
        if type(op1) == Transform: 
            transform_preds = op1.predicates 
        else: 
            transform_preds = op2.predicates 

        if type(op1) == Aggregate: 
            agg_preds = op1.predicates 
        else: 
            agg_preds = op2.predicates 
        

        if '.' in transform_preds: 
            table_transform, col_transform = transform_preds.split(".")
        else: 
            col_transform = None 

        if '.' in agg_preds: 
            table_agg, col_agg = agg_preds.split(".")
        else: 
            col_filter = None
        
        if '.' in transform_preds and '.' in agg_preds and col_transform == col_agg: 
            return False
        elif ('UID' in transform_preds or 'UID' in agg_preds) and (col_agg in PERSON_ID_COLS or col_transform in PERSON_ID_COLS): 
            return False 
        else: 
            return True 
    elif type(op1) == Filter and type(op2) == Transform: 
        transform_preds = op2.predicates 
        filter_preds = op1.predicate 

        if '.' in transform_preds: 
            table_transform, col_transform = transform_preds.split(".")
        else: 
            col_transform = None 

        if '.' in filter_preds: 
            table_filter, col_filter = filter_preds.split(".")
        else: 
            col_filter = None
        
        if '.' in transform_preds and '.' in filter_preds and col_transform == col_filter: 
            return False
        elif ('UID' in transform_preds or 'UID' in filter_preds) and (col_filter in PERSON_ID_COLS or col_transform in PERSON_ID_COLS): 
            return False 
        else: 
            return True 
    else: 
        print("OP1: {} OP2: {}".format(op1, op2))
        raise NotImplementedError


def swap_nodes(graph, a, b): 
    # all nodes pointing to a should point to b now 
    # all nodes b pointed to, a should point to 
    for node, out in graph.items(): 
        if a in out: 
            out[:] = [x if x != a else b for x in out]
    tmp = graph[b]
    graph[a] = graph[b]
    return graph 


def inject_node(graph, a, b): 
    graph[a] = b
    return graph


def make_move(graph, roots):
    inner_frontier = [roots]
    result_graph = None 

    while len(inner_frontier) > 0: 
        rootset = inner_frontier.pop(0)
        found = False 
        for root in rootset: 
            # print('graph: {}'.format(graph))
            connected = None 
            rootnode = None
            for node, conn in graph.items(): 
                # print('node name: {} basetable: {}'.format(node, root))
                if node is not None and node.name == root:
                    # print('made it!')
                    connected = conn
                    rootnode = node 
            
            if rootnode is None:
                print("COULDNT FIND {}, continuing.".format(root)) 
                continue 

            if rootnode.operation_type is None: 
                print("NO OPTYPE {}, continuing.".format(root)) 
                continue 

            if connected is None: 
                print("COULDNT FIND {}'s CONNECTED, continuing.".format(root)) 
                continue 
            else: 
                print('why')

            num_commutative = 0
            # print('connected: {}'.format(connected))
            for node in connected: 
                # print('rootnode: {}'.format(rootnode))
                commutative = check_commutativity(rootnode, node)
                if commutative: 
                    num_commutative += 1 

            if num_commutative == len(connected): 
                found = True 
                result_graph = swap_nodes(graph.copy, rootnode, node)
            else: 
                print('ONLY {}/{} children commutative. '.format(num_commutative, len(connected)))
        if not found: 
            for root in rootset: 
                if rootnode in graph: 
                    inner_frontier.append(graph[rootnode])
        else: 
            break 
    
    return result_graph 


def merge_graphs(graph1, graph2): 
    new_graph = graph1.copy()
    for node, connected in new_graph.items(): 
        if node in graph2: 
            connected2 = graph2[node]
            for conn in connected2:
                if conn not in graph1[node]:
                    print("adding {} to graph".format(node))
                    new_graph[node].append(conn)

    for node, connected in graph2.items(): 
        if node not in new_graph: 
            new_graph[node] = connected 

    return new_graph 


def planning(queries, policies): 
    print('STARTING PLANNING *********************************')

    # insert policy nodes directly below basetables, prior to any query computation nodes.
    # this configuration will always be correct but it is clearly not optimal.
    query = queries[0]
    print('QUERY: {}'.format(query))
    print('POLICIES: {}'.format(policies[0]))

    new_base_tables = {}
    for policy in policies: 
        for node, connected in policy.items(): 
            if len(connected) == 0: 
                if node.exported_as is not None: 
                    new_base_tables[node.exported_as] = node
                
    
    merged_policy_graph = policies[0]
    for i, policy in enumerate(policies): 
        if i > 0: 
            merged_policy_graph = merge_graphs(merged_policy_graph, policy)
  
    new_query = query.copy()
    for node, connected in query.items(): 
        if node.name in new_base_tables: 
            replacement = new_base_tables[node.name]
            new_query[replacement] = connected
            del new_query[node]

    unoptimized_graph = merge_graphs(merged_policy_graph, new_query)
    
    # now, our goal is to push the policy nodes as far down in the graph as possible.
    # we do this by comparing every policy node and its neighbor and seeing if we can 
    # swap their positions (aka, if the operations commute). we stop once we've reached 
    # a fixed point. everytime we make a change, we take a snapshot of the resulting graph.
    # TODO what happens at a branching point? in this case, it's no longer
    # necessarily better to push down the policy node. initial heuristic: if the node is
    # user dependent, continue to push it down, otherwise don't. TODO include the branching
    # factor in this cost model?

    start_graph = unoptimized_graph.copy()
    frontier = [unoptimized_graph]
    all_graphs = [unoptimized_graph]

    while len(frontier) > 0: 
        graph = frontier.pop(0)
        new_graph = make_move(graph.copy(), new_base_tables.keys()) 
        if new_graph is not None: 
            frontier.append(new_graph) 
            frontier.append(graph)
            all_graphs.append(new_graph)

    return all_graphs 
    