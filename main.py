import os
import struct

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
            print(f"Inserted key={key}, value={value}.")
        except ValueError:
            print("Invalid input.")

    def search(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        try:
            key = int(input("Enter key to search (unsigned integer): "))
            print(f"Search result: key={key}, value=<value>.")
        except ValueError:
            print("Invalid input.")

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
                    print(f"Loaded key={key}, value={value}.")
                except ValueError:
                    print("Error")

    def print_index(self):
        if not self.currentFile:
            print("No file is currently open.")
            return
        print("Printing all key/value pairs.")

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
            print(f"Extracted key/value pairs to '{name}'.")

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
            "print": self.print_index,
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
