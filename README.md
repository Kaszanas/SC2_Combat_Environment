# SC2 Combat Detector

This project introduces a way of reproducing real combat scenarios observable in StarCraft 2 replays for automated agents to play against. It is split into a couple of parts (this may change in the future):
1. **Combat Detection**: Detects combat in StarCraft 2 replays, and saves intermediate files required to reproduce the environment.
2. **Combat Reproduction**: Reproduces the combat scenarios for experiments.

Note that this project is in active development and is subject to change. If you wish to see any changes or contribute, please open an issue and discuss your use case.

## Running the Project

There are a few steps required before you can run the project. Please note that the development environment setup will vary based on the operating system you are using. If you have issues running the project, please open an issue on GitHub and document it as much as possible.

### Setting up the Environment

I have followed the steps below to set up my environment. Due to the lack of Linux support for StarCraft 2 and headless mode. I have used Windows 11 operating system for development and testing. If at any point this software fails to run, make sure that you are able to run the StarCraft 2 and replays manually.

1. Install StarCraft 2 and ensure you can run it.
2. Acquire the replays that you will use.
   1. Acquire all of the replay dependencies. This can be done with [SC2InfoExtractorGo](https://github.com/Kaszanas/SC2InfoExtractorGo) and the flag specifying that you want to download all dependencies.
   2. Place the replay dependencies in the correct `Cache` directory of StarCraft 2. On Windows this is located at `C:\ProgramData\Blizzard Entertainment\Battle.net\Cache`. If you are using a different operating system, please refer to this code [pysc2_evolved update_battle_net_cache.py](https://github.com/Kaszanas/pysc2_evolved/blob/dev/src/pysc2_evolved/bin/update_battle_net_cache.py). This project does not support other operating systems at the moment. Another tool that can be used to copy the replay dependencies to their destination is the code introduced in [DatasetPreparator](https://github.com/Kaszanas/DatasetPreparator/pull/73). If at any point you receive error messages about missing dependencies, please debug the issue by checking if the dependencies are in the correct location.
   3. Acquire all of the required game versions for running the replays. The best way to do this is to download the [CascView Program](http://www.zezula.net/en/casc/main.html), run the software, open the s2 online storage, and download all of the game versions. Please note, that the online storage keeps the version names with lowercase `base` names and lowercase `sc2_*.exe` names. This can cause some issues when running the game. It is best to ensure that these names are uppercase. The game versions are stored in the installation directory of StarCraft 2 under the `Versions` directory. For example, `C:\Program Files (x86)\StarCraft II\Versions\Base75689`.
3. Install [uv](https://github.com/astral-sh/uv) for Python dependency management.
   1. Install the project dependencies by running `uv sync`.
   2. Activate the virtual environment.
4. Acquire the protobuf compiler `protoc` as described in [Compiling Protobuf](#compiling-protobuf).
   1. Run `make compile_protos` to compile the protobuf files. If you do not wish to use make, please open the file and see the commands that are run to compile the protobuf files. You can run them manually.
5. Run the `sc2_combat_detector/main.py` with the required arguments. This program should open the replays using `pysc2_evolved`, acquire all of the required observations, perform the combat detection functionality, and save the results to the specified directories.
6. Run the `sc2_combat_reproduction/main.py` with the required arguments. This program should create an environment that reproduces the combat scenarios detected in the previous step. This code is meant to showcase re-creating the combat scenarios for agent training or for evaluating the human performance.


### Compiling Protobuf

To compile protobuf protoc is required. Currently, the project uses a quite old version of protoc to ensure compatibility with legacy code left in parts of the project. Hopefully this will be resolved in the future.

1. Download the protoc from the following release:
   - https://github.com/protocolbuffers/protobuf/releases/v3.20.1
   - Windows download: https://github.com/protocolbuffers/protobuf/releases/download/v3.20.1/protoc-3.20.1-win64.zip
2. Run `make compile_protos` to compile the protobuf files.
