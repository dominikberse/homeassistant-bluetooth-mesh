import logging

from uuid import UUID


class Node:
    """
    Abstraction layer for specific mesh node types
    """

    def __init__(self, uuid, type, unicast, count):
        self.uuid = uuid
        self.type = type
        self.unicast = unicast
        self.count = count
        self.hass = None

    def __str__(self):
        id = self.hass and self.hass.optional('id')
        
        if id:
            return f'{id} ({self.uuid}, {self.unicast:04})' 
        return f'{self.uuid} ({self.unicast:04})'

    async def bind(self, app):
        """
        Configure the node to work with the available mesh clients
        """
        self._app = app

    def print_info(self):
        print(
            f'\t{self.uuid}:\n'
            f'\t\ttype: {self.type}\n'
            f'\t\tunicast: {self.unicast} ({self.count})\n'
        )

    def yaml(self):
        # UUID is used as key and does not need to be stored
        return {
            'type': self.type,
            'unicast': self.unicast,
            'count': self.count,
        }


class NodeManager:
    """
    Specific store to manage nodes

    Notice that the interface is slightly different, due to the use of UUIDs as keys.
    Therefore no inheritance is implemented.
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
