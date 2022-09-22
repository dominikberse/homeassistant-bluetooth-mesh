import logging

from uuid import UUID


class NodeManager:
    """
    Specific store to manage nodes

    Notice that the interface is slightly different, due to the use of UUIDs as keys.
    Therefore no inheritance from tools.Store is implemented.
    """
    
    def __init__(self, store, types):
        self._store = store
        self._types = types
        self._nodes = {}

        # create node instances of specific types
        for uuid, info in self._store.items():
            self._nodes[uuid] = self._make_node(UUID(uuid), info)

    def __len__(self):
        return len(self._nodes)

    def _make_node(self, uuid, info):
        typename = info.get('type')
        if typename is None or typename not in self._types:
            raise Exception(f'Invalid node type "{typename}" for {uuid}')

        # create node instance of specific type
        return self._types[typename](uuid, **info)

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