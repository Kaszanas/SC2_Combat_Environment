


.PHONY: get_protoc
get_protoc:
	@echo "Not implemented yet."


.PHONY: compile_protos
compile_protos:
	@echo "Compiling Protobuf files..."
	protoc-3.20.1-win64/bin/protoc -I=./src/proto \
		-I=./src/proto/s2client-proto \
		--python_out=./src/sc2_combat_detector/proto \
		./src/proto/observation_collection.proto
