import subprocess
import json
import os


def main() -> None:
    with open("demo_network_structure.json") as f:
        demo_network = json.load(f)
    subprocesses = []
    for alias in range(demo_network["size"]):
        out_file = open('node' + str(alias) + 'out.txt', "w")
        err_file = open('node' + str(alias) + 'err.txt', "w")
        process = subprocess.Popen("python demo_node.py " + str(alias), shell = True, stdout = out_file, stderr=err_file)
        subprocesses.append(process)
        out_file.close()
        err_file.close()
    while True:
        try:
            command = input()
            if command == "exit":
                for process in subprocesses:
                    process.kill()
                os._exit(0)
            elif command == "see_node":
                alias = input("node_alias: ")
                with open('node' + str(alias) + 'out.txt', 'r') as f:
                    print(f.read().decode("utf-8"))
                    # print(f.read())
        except EOFError:
            for process in subprocesses:
                process.kill()
            os._exit(0)

if __name__ == "__main__":
    main()