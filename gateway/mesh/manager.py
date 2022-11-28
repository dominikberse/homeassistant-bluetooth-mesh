import logging

from uuid import UUID


class NodeManager:
    """
    Specific store to manage nodes

    Notice that the interface is slightly different, due to the use of UUIDs as keys.
    Therefore no inheritance from tools.Store is implemented.
    """
    
    def __init__(self, store, config, types):
        self._store = store
        self._types = types
        self._nodes = {}

        # create node instances of specific types
        for uuid, info in self._store.items():
            node_config = config.node_config(uuid)
            self._nodes[uuid] = self._make_node(UUID(uuid), info, node_config)

    def __len__(self):
        return len(self._nodes)

    def _make_node(self, uuid, info, node_config=None):
        typename = info.get('type')

        # check if the user changed the node type in the configuration
        # this needs to be done here, before the actual node class is instanciated
        if node_config:
            user_typename = node_config.optional('type', typename)
            if user_typename != typename:
                logging.warning(f'Node type changed for {uuid} from "{typename}" to "{user_typename}"')
            
                typename = user_typename
                info['type'] = typename

        if typename is None or typename not in self._types:
            raise Exception(f'Invalid node type "{typename}" for {uuid}')

        # create node instance of specific type
        return self._types[typename](uuid, config=node_config, **info)

    def get(self, uuid):
        return self._nodes.get(str(uuid))

    def has(self, uuid):
        return str(uuid) in self._nodes

    def persist(self):
        # TODO: maybe update store instead of recreating it
        # this is currently neccessary to reflect deletions
        self._store.reset()

        for node in self._nodes.values():
            self._store.set(str(node.uuid), node.yaml())
        self._store.persist()

    def add(self, node):
        if str(node.uuid) in self._nodes:
            logging.warning(f'Node {node} already exists')
        self._nodes[str(node.uuid)] = node

    def create(self, uuid, info):
        self.add(self._make_node(uuid, info))

    def delete(self, uuid):
        del self._nodes[str(uuid)]
        
    def all(self):
        return self._nodes.values()

    def reset(self):
        self._nodes.clear()