from typing import List, TypedDict


class LocalVarDict(TypedDict):
    name: str
    typeName: str
    valueRepr: str
    valueTrunc: bool


type LocalVarList = List[LocalVarDict]


class SourceLines(TypedDict):
    lineno: int
    code: str
    isTarget: bool


type SourceContext = List[SourceLines]


class FrameDict(TypedDict):
    filename: str
    lineno: int
    functionName: str
    locals: LocalVarList
    sourceContext: SourceContext


type FrameList = List[FrameDict]
