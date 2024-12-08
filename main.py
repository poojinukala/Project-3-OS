import os
import struct

class BTreeNode:
    blockSize = 512
    maxKey = 19
    maxChild = 20

    def __init__(self, id, parentId=0):
        self.id = id
        self.parentId = parentId
        self.pairs = 0
        self.keys = [0] * self.maxKey
        self.values = [0] * self.maxKey
        self.children = [0] * self.maxChild

    def serialize(self):
        data = struct.pack('>Q', self.id)
        data += struct.pack('>Q', self.parentId)
        data += struct.pack('>Q', self.pairs)
        for i in range(self.pairs):
            data += struct.pack('>Q', self.keys[i])
            data += struct.pack('>Q', self.values[i])
        for child in self.children:
            data += struct.pack('>Q', child)
        padding = self.blockSize - len(data)
        data += b'\x00' * padding
        return data

    @classmethod
    def deserialize(cls, data):
        id = struct.unpack('>Q', data[0:8])[0]
        parentId = struct.unpack('>Q', data[8:16])[0]
        pairs = struct.unpack('>Q', data[16:24])[0]
        offset = 24
        keys = []
        values = []
        for i in range(pairs):
            keys.append(struct.unpack('>Q', data[offset:offset + 8])[0])
            offset += 8
            values.append(struct.unpack('>Q', data[offset:offset + 8])[0])
            offset += 8
        children = [struct.unpack('>Q', data[offset + i * 8:offset + (i + 1) * 8])[0] for i in range(cls.maxChild)]
        node = cls(id, parentId)
        node.pairs = pairs
        node.keys[:pairs] = keys
        node.values[:pairs] = values
        node.children = children
        return node


class BTreeIndex:
    def __init__(self):
        self.currentFile = None
        self.filePath = None

    def create(self):
        name = input("Enter the name of the new index file: ").strip()
        if os.path.exists(name):
            overwrite = input("File exists. Overwrite? (yes/no): ").strip().lower()
            if overwrite != 'yes':
                print("Quitting")
                return
        with open(name, 'wb') as f:
            f.write(b'4337PRJ3')
            f.write(struct.pack('>Q', 0))
            f.write(struct.pack('>Q', 1))
        self.filePath = name
        self.currentFile = open(self.filePath, 'r+b')
        print(f"File '{name}' created and opened.")

    def openingFile(self):
        name = input("Enter the name of the index file to open: ").strip()
        if not os.path.exists(name):
            print("File does not exist.")
            return
        with open(name, 'rb') as f:
            header = f.read(16)
            if len(header) < 16:
                print("Invalid file format.")
                return
        self.filePath = name
        self.currentFile = open(self.filePath, 'r+b')
        print(f"File '{name}' opened.")

    def insert(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        try:
            key = int(input("Enter key (unsigned integer): "))
            value = int(input("Enter value (unsigned integer): "))
            self.currentFile.seek(0)
            header = self.currentFile.read(24)
            rootId = struct.unpack('>Q', header[8:16])[0]
            if rootId == 0:
                rootNode = BTreeNode(id=1)
                rootNode.keys[0] = key
                rootNode.values[0] = value
                rootNode.pairs = 1
                self.currentFile.seek(512)
                self.currentFile.write(rootNode.serialize())
                self.currentFile.seek(8)
                self.currentFile.write(struct.pack('>Q', 1))
            else:
                self.insertToBtree(rootId, key, value)
            print(f"Inserted key={key}, value={value}.")
        except ValueError:
            print("Invalid input.")

    def insertToBtree(self, id, key, value):
        self.currentFile.seek(id * 512)
        data = self.currentFile.read(512)
        node = BTreeNode.deserialize(data)

        i = 0
        while i < node.pairs and key > node.keys[i]:
            i += 1

        if i < node.pairs and node.keys[i] == key:
            print(f"Error: Key {key} already exists.")
            return

        if node.pairs < BTreeNode.maxKey:
            node.keys.insert(i, key)
            node.values.insert(i, value)
            node.keys.pop()
            node.values.pop()
            node.pairs += 1

            self.currentFile.seek(id * 512)
            self.currentFile.write(node.serialize())
        else:
            print("Node splitting required (not implemented).")


    def search(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        try:
            key = int(input("Enter key to search (unsigned integer): "))
            self.currentFile.seek(0)
            header = self.currentFile.read(24)
            rootId = struct.unpack('>Q', header[8:16])[0]
            if rootId == 0:
                print("Tree is empty.")
                return
            value = self.searchBtree(rootId, key)
            if value is not None:
                print(f"Search result: key={key}, value={value}.")
            else:
                print(f"Key {key} not found.")
        except ValueError:
            print("Invalid input.")

    def searchBtree(self, id, key):
        self.currentFile.seek(id * 512)
        data = self.currentFile.read(512)
        node = BTreeNode.deserialize(data)
        i = 0
        while i < node.pairs and key > node.keys[i]:
            i += 1
        if i < node.pairs and node.keys[i] == key:
            return node.values[i]
        if node.children[i] == 0:
            return None
        return self.searchBtree(node.children[i], key)

    def load(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        name = input("Enter the file name: ").strip()
        if not os.path.exists(name):
            print("File does not exist.")
            return
        with open(name, 'r') as f:
            for line in f:
                try:
                    key, value = map(int, line.strip().split(','))
                    self.insertKeyValue(key, value)
                    print(f"Loaded key={key}, value={value}.")
                except ValueError:
                    print("Error in file format.")

    def insertKeyValue(self, key, value):
        self.currentFile.seek(0)
        header = self.currentFile.read(24)
        rootId = struct.unpack('>Q', header[8:16])[0]
        if rootId == 0:
            rootNode = BTreeNode(id=1)
            rootNode.keys[0] = key
            rootNode.values[0] = value
            rootNode.pairs = 1
            self.currentFile.seek(512)
            self.currentFile.write(rootNode.serialize())
            self.currentFile.seek(8)
            self.currentFile.write(struct.pack('>Q', 1))
        else:
            self.insertToBtree(rootId, key, value)

    def printIndex(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        self.currentFile.seek(0)
        header = self.currentFile.read(24)
        rootId = struct.unpack('>Q', header[8:16])[0]
        if rootId == 0:
            print("Tree is empty.")
            return
        self.printBtree(rootId)

    def printBtree(self, id):
        self.currentFile.seek(id * 512)
        data = self.currentFile.read(512)
        node = BTreeNode.deserialize(data)
        for i in range(node.pairs):
            if node.children[i] != 0:
                self.printBtree(node.children[i])
            print(f"Key: {node.keys[i]}, Value: {node.values[i]}")
        if node.children[node.pairs] != 0:
            self.printBtree(node.children[node.pairs])

    def extract(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        name = input("Enter the file name: ").strip()
        if os.path.exists(name):
            overwrite = input("File exists. Overwrite? (yes/no): ").strip().lower()
            if overwrite != 'yes':
                print("Quitting")
                return
        with open(name, 'w') as f:
            self.currentFile.seek(0)
            header = self.currentFile.read(24)
            rootId = struct.unpack('>Q', header[8:16])[0]
            if rootId == 0:
                print("Tree is empty.")
                return
            self.extractBtree(rootId, f)
        print(f"Extracted key/value pairs to '{name}'.")

    def extractBtree(self, id, file):
        self.currentFile.seek(id * 512)
        data = self.currentFile.read(512)
        node = BTreeNode.deserialize(data)
        for i in range(node.pairs):
            if node.children[i] != 0:
                self.extractBtree(node.children[i], file)
            file.write(f"{node.keys[i]},{node.values[i]}\n")
        if node.children[node.pairs] != 0:
            self.extractBtree(node.children[node.pairs], file)

    def quit(self):
        if self.currentFile:
            self.currentFile.close()
        print("Exiting program.")
        exit(0)

    def menu(self):
        commands = {
            "create": self.create,
            "open": self.openingFile,
            "insert": self.insert,
            "search": self.search,
            "load": self.load,
            "print": self.printIndex,
            "extract": self.extract,
            "quit": self.quit,
        }
        while True:
            print("\nCommands: create, open, insert, search, load, print, extract, quit")
            command = input("Enter a command: ").strip().lower()
            if command in commands:
                commands[command]()
            else:
                print("Invalid command.")

if __name__ == "__main__":
    index = BTreeIndex()
    index.menu()
