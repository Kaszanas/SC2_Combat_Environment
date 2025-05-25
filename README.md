## SC2 Combat Detector

This project introduces a way of reproducing real combat scenarios observable in StarCraft 2 replays for automated agents to play against. It is split into a couple of parts (this may change in the future):
1. **Combat Detection**: Detects combat in StarCraft 2 replays, and saves intermediate files required to reproduce the environment.
2. **Combat Reproduction**: Reproduces the combat scenarios for experiments.

### Compiling Protobuf

To compile protobuf protoc is required. Currently, the project uses a quite old version of protoc to ensure compatibility with legacy code left in parts of the project. Hopefully this will be resolved in the future.

1. Download the protoc from the following release:
   - https://github.com/protocolbuffers/protobuf/releases/v3.20.1
   - Windows download: https://github.com/protocolbuffers/protobuf/releases/download/v3.20.1/protoc-3.20.1-win64.zip
2. Run `make compile_protos` to compile the protobuf files.
