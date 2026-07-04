@0xa93ea69fddfdcace;

struct SourceLine {
    lineno @0 :Int32;
    code @1 :Text;
    isTarget @2 :Bool;
}

struct Variable {
    name @0 :Text;
    typeName @1 :Text;
    valueRepr @2 :Text;
    valueTrunc @3 :Bool;
}

struct StackFrame {
    filename @0 :Text;
    lineno @1 :Int32;
    functionName @2 :Text;
    locals @3 :List(Variable);
    sourceContext @4 :List(SourceLine);
}

struct ExceptionReport {
    exceptionType @0 :Text;
    exceptionValue @1 :Text;
    traceback @2 :List(StackFrame);
    timestamp @3 :Float64;
}

