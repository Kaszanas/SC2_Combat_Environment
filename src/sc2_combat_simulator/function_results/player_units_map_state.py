from dataclasses import dataclass
from typing import List

import s2clientprotocol.raw_pb2 as sc2proto_raw_pb


@dataclass
class PlayerUnitsMapState:
    player1_units: List[sc2proto_raw_pb.Unit]
    player2_units: List[sc2proto_raw_pb.Unit]
    player1_map_state: sc2proto_raw_pb.MapState
    player2_map_state: sc2proto_raw_pb.MapState
