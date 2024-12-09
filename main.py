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
    
    # Serializes the node data into a fixed-size byte structure for file storage.
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
    # Deserializes the given byte structure into a BTreeNode object.
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
    # Initializes the BTreeIndex object with no file open.
    def __init__(self):
        self.currentFile = None
        self.filePath = None

    # Creates a new index file, writing the initial headers and opening it for use.
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

    # Opens an existing index file for reading and writing if it exists and has valid format.
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

    # Inserts a single key-value pair into the B-tree, creating a root if none exists.
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
                self.writeNode(rootNode)
                self.currentFile.seek(8)
                self.currentFile.write(struct.pack('>Q', 1))
            else:
                self.insertToBtree(rootId, key, value)
            print(f"Inserted key={key}, value={value}.")
        except ValueError:
            print("Invalid input.")

    # Recursively inserts a key-value pair into the correct place in the B-tree.
    def insertToBtree(self, id, key, value):
        node = self.readNode(id)

        i = 0
        while i < node.pairs and key > node.keys[i]:
            i += 1

        if i < node.pairs and node.keys[i] == key:
            print(f"Error: Key {key} already exists.")
            return

        if node.children[0] == 0:
            if node.pairs < BTreeNode.maxKey:
                for j in range(node.pairs, i, -1):
                    node.keys[j] = node.keys[j-1]
                    node.values[j] = node.values[j-1]
                node.keys[i] = key
                node.values[i] = value
                node.pairs += 1
                self.writeNode(node)
            else:
                self.splitNode(node, key, value, isLeaf=True)
        else:
            self.insertToBtree(node.children[i], key, value)

    # Splits a full node into two nodes and promotes the median key to the parent.
    def splitNode(self, node, key, value, isLeaf=False):
        allKeys = node.keys[:node.pairs] + [key]
        allValues = node.values[:node.pairs] + [value]

        # Sort by key
        zipped = list(zip(allKeys, allValues))
        zipped.sort(key=lambda x: x[0])
        keys, values = zip(*zipped)
        keys = list(keys)
        values = list(values)

        midIndex = len(keys) // 2
        medianKey = keys[midIndex]
        medianValue = values[midIndex]

        leftNode = BTreeNode(self.getNextBlockId(), node.parentId)
        rightNode = BTreeNode(self.getNextBlockId(), node.parentId)

        # Split a leaf node
        if isLeaf:
            leftNode.pairs = midIndex
            for i in range(midIndex):
                leftNode.keys[i] = keys[i]
                leftNode.values[i] = values[i]

            rightNode.pairs = len(keys) - midIndex - 1
            for i in range(rightNode.pairs):
                rightNode.keys[i] = keys[midIndex + 1 + i]
                rightNode.values[i] = values[midIndex + 1 + i]

            for i in range(BTreeNode.maxChild):
                leftNode.children[i] = 0
                rightNode.children[i] = 0
        
        # Split an internal node
        else:
            pk = list(keys)
            pv = list(values)
            pc = list(node.children[:node.pairs+1])

            leftNode.pairs = midIndex
            for i in range(midIndex):
                leftNode.keys[i] = pk[i]
                leftNode.values[i] = pv[i]
                leftNode.children[i] = pc[i]
            leftNode.children[midIndex] = pc[midIndex]

            rightPairs = len(pk) - midIndex - 1
            rightNode.pairs = rightPairs
            for i in range(rightPairs):
                rightNode.keys[i] = pk[midIndex+1+i]
                rightNode.values[i] = pv[midIndex+1+i]
                rightNode.children[i] = pc[midIndex+1+i]
            rightNode.children[rightPairs] = pc[-1]

        # Create a new root if we split the root
        if node.parentId == 0:
            newRoot = BTreeNode(self.getNextBlockId())
            newRoot.keys[0] = medianKey
            newRoot.values[0] = medianValue
            newRoot.children[0] = leftNode.id
            newRoot.children[1] = rightNode.id
            newRoot.pairs = 1

            self.currentFile.seek(8)
            self.currentFile.write(struct.pack('>Q', newRoot.id))

            self.writeNode(newRoot)
            self.writeNode(leftNode)
            self.writeNode(rightNode)
        # Insert median key into the parent
        else:
            parentNode = self.readNode(node.parentId)
            i = 0
            while i < parentNode.pairs and parentNode.keys[i] < medianKey:
                i += 1

            if parentNode.pairs < BTreeNode.maxKey:
                for j in range(parentNode.pairs, i, -1):
                    parentNode.keys[j] = parentNode.keys[j-1]
                    parentNode.values[j] = parentNode.values[j-1]
                    parentNode.children[j+1] = parentNode.children[j]

                parentNode.keys[i] = medianKey
                parentNode.values[i] = medianValue
                parentNode.children[i] = leftNode.id
                parentNode.children[i+1] = rightNode.id
                parentNode.pairs += 1

                self.writeNode(parentNode)
                self.writeNode(leftNode)
                self.writeNode(rightNode)
            # If parent is also full, split it as well
            else:
                pk = list(parentNode.keys[:parentNode.pairs])
                pv = list(parentNode.values[:parentNode.pairs])
                pc = list(parentNode.children[:parentNode.pairs+1])

                pk.insert(i, medianKey)
                pv.insert(i, medianValue)
                pc[i] = leftNode.id
                pc.insert(i+1, rightNode.id)

                # Split the parent
                self.splitParent(parentNode, pk, pv, pc)
                self.writeNode(leftNode)
                self.writeNode(rightNode)

    
    # Splits a full parent node (internal) into two and promotes the median to the grandparent.
    def splitParent(self, parentNode, pk, pv, pc):
        midIndex = len(pk)//2
        medianKey = pk[midIndex]
        medianValue = pv[midIndex]

        leftNode = parentNode
        rightNode = BTreeNode(self.getNextBlockId(), leftNode.parentId)

        leftNode.pairs = midIndex
        for i in range(midIndex):
            leftNode.keys[i] = pk[i]
            leftNode.values[i] = pv[i]
            leftNode.children[i] = pc[i]
        leftNode.children[midIndex] = pc[midIndex]
        for i in range(midIndex, BTreeNode.maxKey):
            leftNode.keys[i] = 0
            leftNode.values[i] = 0
        for i in range(midIndex+1, BTreeNode.maxChild):
            leftNode.children[i] = 0

        rightPairs = len(pk) - midIndex - 1
        rightNode.pairs = rightPairs
        for i in range(rightPairs):
            rightNode.keys[i] = pk[midIndex+1+i]
            rightNode.values[i] = pv[midIndex+1+i]
            rightNode.children[i] = pc[midIndex+1+i]
        rightNode.children[rightPairs] = pc[-1]
        
        # Create a new root if splitting was at the top
        if leftNode.parentId == 0:
            newRoot = BTreeNode(self.getNextBlockId())
            newRoot.keys[0] = medianKey
            newRoot.values[0] = medianValue
            newRoot.children[0] = leftNode.id
            newRoot.children[1] = rightNode.id
            newRoot.pairs = 1

            self.currentFile.seek(8)
            self.currentFile.write(struct.pack('>Q', newRoot.id))

            self.writeNode(newRoot)
            self.writeNode(leftNode)
            self.writeNode(rightNode)
        else:
            # Insert median into the grandparent
            grandParentNode = self.readNode(leftNode.parentId)
            i = 0
            while i < grandParentNode.pairs and grandParentNode.keys[i] < medianKey:
                i += 1
            if grandParentNode.pairs < BTreeNode.maxKey:
                for j in range(grandParentNode.pairs, i, -1):
                    grandParentNode.keys[j] = grandParentNode.keys[j-1]
                    grandParentNode.values[j] = grandParentNode.values[j-1]
                    grandParentNode.children[j+1] = grandParentNode.children[j]
                grandParentNode.keys[i] = medianKey
                grandParentNode.values[i] = medianValue
                grandParentNode.children[i] = leftNode.id
                grandParentNode.children[i+1] = rightNode.id
                grandParentNode.pairs += 1

                self.writeNode(grandParentNode)
                self.writeNode(leftNode)
                self.writeNode(rightNode)
            else:
                pass
    
    # Increments and returns the next available block ID for node storage.
    def getNextBlockId(self):
        self.currentFile.seek(16)
        nextID = struct.unpack('>Q', self.currentFile.read(8))[0]
        self.currentFile.seek(16)
        self.currentFile.write(struct.pack('>Q', nextID + 1))
        return nextID

    # Writes the given node's data into the file at the correct block position.
    def writeNode(self, node):
        self.currentFile.seek(node.id * BTreeNode.blockSize)
        self.currentFile.write(node.serialize())

    # Reads and returns the node stored at the given block ID.
    def readNode(self, id):
        self.currentFile.seek(id * BTreeNode.blockSize)
        data = self.currentFile.read(BTreeNode.blockSize)
        return BTreeNode.deserialize(data)

    # Searches for a key in the B-tree and prints its value if found.
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
    
    # Recursively searches the B-tree for the given key.
    def searchBtree(self, id, key):
        node = self.readNode(id)
        i = 0
        while i < node.pairs and key > node.keys[i]:
            i += 1
        if i < node.pairs and node.keys[i] == key:
            return node.values[i]
        if node.children[i] == 0:
            return None
        return self.searchBtree(node.children[i], key)

    # Loads key-value pairs from a file and inserts them into the B-tree.
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

    # Inserts a given key-value pair into the B-tree if the root exists or creates a new root otherwise.
    def insertKeyValue(self, key, value):
        self.currentFile.seek(0)
        header = self.currentFile.read(24)
        rootId = struct.unpack('>Q', header[8:16])[0]
        if rootId == 0:
            rootNode = BTreeNode(id=1)
            rootNode.keys[0] = key
            rootNode.values[0] = value
            rootNode.pairs = 1
            self.writeNode(rootNode)
            self.currentFile.seek(8)
            self.currentFile.write(struct.pack('>Q', 1))
        else:
            self.insertToBtree(rootId, key, value)

    # Prints the entire B-tree in a Root/Children hierarchical format.
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

        rootNode = self.readNode(rootId)
        print("Root:")
        for i in range(rootNode.pairs):
            print(f"  Key: {rootNode.keys[i]}, Value: {rootNode.values[i]}")

        for childIndex in range(rootNode.pairs + 1):
            if rootNode.children[childIndex] != 0:
                if childIndex == 0:
                    label = "Left Child:"
                elif childIndex == 1:
                    label = "Right Child:"
                else:
                    label = f"Child {childIndex + 1}:"
                self.printChild(rootNode.children[childIndex], label, 1)

    # Recursively prints a subtree starting from the given node with the specified label and indentation.
    def printChild(self, id, label, level):
        node = self.readNode(id)
        indent = "  " * level
        print(f"{indent}{label}")
        for i in range(node.pairs):
            print(f"{indent}  Key: {node.keys[i]}, Value: {node.values[i]}")
        for childIndex in range(node.pairs + 1):
            if node.children[childIndex] != 0:
                if childIndex == 0:
                    childLabel = "Left Child:"
                elif childIndex == 1:
                    childLabel = "Right Child:"
                else:
                    childLabel = f"Child {childIndex + 1}:"
                self.printChild(node.children[childIndex], childLabel, level + 1)

    # Extracts all key-value pairs from the B-tree into a specified file in sorted order.
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

    # Recursively performs in-order traversal to extract key-value pairs into a file.
    def extractBtree(self, id, file):
        node = self.readNode(id)
        for i in range(node.pairs):
            if node.children[i] != 0:
                self.extractBtree(node.children[i], file)
            file.write(f"{node.keys[i]},{node.values[i]}\n")
        if node.children[node.pairs] != 0:
            self.extractBtree(node.children[node.pairs], file)

    # Closes the current file and exits the program.
    def quit(self):
        if self.currentFile:
            self.currentFile.close()
        print("Exiting program.")
        exit(0)

    # Displays a command menu and executes commands until the user quits.
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
