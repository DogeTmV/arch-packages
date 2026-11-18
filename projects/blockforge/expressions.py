"""Language-neutral expressions for blockforge fields.

A field such as ``score + random(1, 4)`` is written once in the editor and is
translated into idiomatic C++ or Rust by :func:`translate_expression`.  The
parser is intentionally small: numbers, strings, booleans, variables, calls,
and the usual operators.  Keeping it dependency-free also lets the editor
validate a project without a compiler or a display server.
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Sequence, Tuple


class ExpressionError(ValueError):
    """Raised when a block field is not a valid blockforge expression."""


@dataclass(frozen=True)
class ExprContext:
    """Translation context supplied by the code generator."""

    language: str
    sprite: int = 0
    variables: Dict[str, str] = None
    sprites: Sequence[str] = ()
    locals: Dict[str, Tuple[str, str]] = None

    def __post_init__(self):
        if self.variables is None:
            object.__setattr__(self, "variables", {})
        if self.locals is None:
            object.__setattr__(self, "locals", {})
        if self.language not in ("cpp", "rust"):
            raise ValueError("unsupported language: %s" % self.language)


# SDL scancodes, shared by both generated languages so a key block behaves the
# same regardless of the chosen target.
KEYS = {
    "space": 44, "up": 82, "down": 81, "left": 80, "right": 79,
    "a": 4, "b": 5, "c": 6, "d": 7, "e": 8, "f": 9, "g": 10,
    "h": 11, "i": 12, "j": 13, "k": 14, "l": 15, "m": 16,
    "n": 17, "o": 18, "p": 19, "q": 20, "r": 21, "s": 22,
    "t": 23, "u": 24, "v": 25, "w": 26, "x": 27, "y": 28, "z": 29,
    "1": 30, "2": 31, "3": 32, "4": 33, "5": 34,
    "6": 35, "7": 36, "8": 37, "9": 38, "0": 39,
    "enter": 40, "return": 40, "escape": 41, "esc": 41,
    "backspace": 42, "tab": 43, "minus": 45, "equals": 46,
    "comma": 54, "period": 55, "slash": 56,
    "shift": 225, "left shift": 225, "ctrl": 224, "control": 224,
    "alt": 226,
}

# name -> (argument count, result type)
BUILTINS = {
    "x position": (0, "num"),
    "y position": (0, "num"),
    "direction": (0, "num"),
    "costume": (0, "num"),
    "size": (0, "num"),
    "timer": (0, "num"),
    "mouse x": (0, "num"),
    "mouse y": (0, "num"),
    "key pressed": (1, "bool"),
    "touching edge": (0, "bool"),
    "touching sprite": (1, "bool"),
    "random": (2, "num"),
    "abs": (1, "num"),
    "sqrt": (1, "num"),
    "sin": (1, "num"),
    "cos": (1, "num"),
    "floor": (1, "num"),
    "ceil": (1, "num"),
    "round": (1, "num"),
    "min": (2, "num"),
    "max": (2, "num"),
    "len": (1, "num"),
    "join": (2, "text"),
    "to text": (1, "text"),
    "to number": (1, "num"),
}

# Names that cannot be used as variables because they are language keywords or
# reserved expressions.  Checked by the project validator, not the parser.
RESERVED = set(BUILTINS) | {"and", "or", "not", "true", "false", "mod"}

_TOKEN = re.compile(
    r'\s+|'
    r'(?P<num>\d+(?:\.\d+)?)|'
    r'(?P<str>"(?:\\.|[^"\\])*")|'
    r'(?P<name>[A-Za-z_][A-Za-z_0-9]*)|'
    r'(?P<op><=|>=|==|!=|&&|\|\||[+\-*/%^<>()!,])'
)

_PRECEDENCE = {
    "or": 1, "||": 1,
    "and": 2, "&&": 2,
    "==": 3, "!=": 3,
    "<": 4, ">": 4, "<=": 4, ">=": 4,
    "+": 5, "-": 5,
    "*": 6, "/": 6, "%": 6,
    "^": 7,
}


@dataclass(frozen=True)
class _Token:
    kind: str
    value: object
    position: int


def _tokenize(source):
    tokens = []
    position = 0
    while position < len(source):
        match = _TOKEN.match(source, position)
        if not match:
            if source[position] == '"':
                raise ExpressionError(
                    "unterminated string at position %d" % position
                )
            raise ExpressionError(
                "unexpected character %r at position %d"
                % (source[position], position)
            )
        position = match.end()
        kind = match.lastgroup
        if kind is None:  # whitespace
            continue
        raw = match.group()
        if kind == "num":
            value = float(raw) if "." in raw else int(raw)
        elif kind == "str":
            value = _unescape(raw[1:-1])
        else:
            value = raw
        tokens.append(_Token(kind, value, match.start()))
    tokens.append(_Token("end", None, len(source)))
    return tokens


def _unescape(raw):
    out = []
    index = 0
    simple = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"'}
    while index < len(raw):
        char = raw[index]
        if char == "\\" and index + 1 < len(raw):
            following = raw[index + 1]
            out.append(simple.get(following, following))
            index += 2
        else:
            out.append(char)
            index += 1
    return "".join(out)


class _Parser:
    def __init__(self, source):
        self.tokens = _tokenize(source)
        self.index = 0

    def peek(self):
        return self.tokens[self.index]

    def take(self):
        token = self.tokens[self.index]
        self.index += 1
        return token

    def parse(self):
        node = self.expression(0)
        if self.peek().kind != "end":
            token = self.peek()
            raise ExpressionError(
                "unexpected %r at position %d" % (token.value, token.position)
            )
        return node

    def expression(self, minimum):
        left = self.prefix()
        while True:
            operator = self.peek()
            name = operator.value
            if operator.kind == "name" and name in ("and", "or"):
                precedence = _PRECEDENCE[name]
            elif operator.kind == "op" and name in _PRECEDENCE:
                precedence = _PRECEDENCE[name]
            else:
                break
            if precedence < minimum:
                break
            self.take()
            if self.peek().kind == "end":
                raise ExpressionError("expression required after %r" % name)
            next_minimum = precedence if precedence == 7 else precedence + 1
            right = self.expression(next_minimum)
            left = ("bin", "and" if name == "&&" else
                    "or" if name == "||" else name, left, right)
        return left

    def prefix(self):
        token = self.take()
        if token.kind == "num":
            return ("num", token.value)
        if token.kind == "str":
            return ("str", token.value)
        if token.kind == "name" and token.value in ("true", "false"):
            return ("bool", token.value == "true")
        if token.kind == "name" and token.value == "not":
            return ("unary", "not", self.expression(8))
        if token.kind == "op" and token.value == "-":
            return ("unary", "-", self.expression(8))
        if token.kind == "op" and token.value == "(":
            node = self.expression(0)
            closing = self.take()
            if closing.value != ")":
                raise ExpressionError("expected ')' at position %d" % closing.position)
            return node
        if token.kind == "name":
            return self._name(token)
        raise ExpressionError(
            "expected an expression at position %d" % token.position
        )

    def _name(self, first):
        words = [first.value]
        while self.peek().kind == "name" and self.peek().value not in ("and", "or"):
            words.append(self.take().value)
        # Prefer the longest builtin so "x position" wins over "x".
        for count in range(len(words), 0, -1):
            candidate = " ".join(words[:count])
            if candidate not in BUILTINS:
                continue
            arity, _ = BUILTINS[candidate]
            arguments = []
            if self.peek().kind == "op" and self.peek().value == "(":
                self.take()
                if self.peek().value != ")":
                    while True:
                        arguments.append(self.expression(0))
                        separator = self.take()
                        if separator.value == ")":
                            break
                        if separator.value != ",":
                            raise ExpressionError(
                                "expected ',' or ')' near position %d"
                                % separator.position
                            )
                else:
                    self.take()
            if len(arguments) != arity:
                raise ExpressionError(
                    "%s expects %d argument(s), got %d"
                    % (candidate, arity, len(arguments))
                )
            return ("call", candidate, arguments)
        if len(words) > 1:
            raise ExpressionError("unknown expression %r" % " ".join(words))
        return ("var", first.value)


def parse_expression(source):
    """Parse *source* into a small, language-neutral tuple AST."""
    if source is None or not str(source).strip():
        raise ExpressionError("expression is empty")
    return _Parser(str(source)).parse()


@dataclass(frozen=True)
class _Typed:
    code: str
    type: str


def _escape(text, language):
    out = str(text).replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return out


def _literal(value, language):
    if isinstance(value, str):
        if language == "cpp":
            return _Typed('std::string("%s")' % _escape(value, language), "text")
        return _Typed('"%s".to_string()' % _escape(value, language), "text")
    if isinstance(value, bool):
        return _Typed("true" if value else "false", "bool")
    number = float(value)
    if language == "rust":
        return _Typed(repr(number), "num")
    return _Typed(str(int(number)) if number.is_integer() else str(number), "num")


class _Translator:
    def __init__(self, context):
        self.context = context
        self.cpp = context.language == "cpp"

    def value(self, typed):
        if self.cpp:
            return typed.code
        return "Value::from(%s)" % typed.code

    def as_num(self, typed):
        if typed.type == "num":
            return typed.code
        if self.cpp:
            return "app.num(%s)" % typed.code
        return "app.num(Value::from(%s))" % typed.code

    def as_bool(self, typed):
        if typed.type == "bool":
            return typed.code
        if self.cpp:
            return "app.as_bool(%s)" % typed.code
        return "app.as_bool(Value::from(%s))" % typed.code

    def visit(self, node):
        kind = node[0]
        return getattr(self, "_%s" % kind)(node)

    def _num(self, node):
        return _literal(node[1], self.context.language)

    def _str(self, node):
        return _literal(node[1], self.context.language)

    def _bool(self, node):
        return _literal(node[1], self.context.language)

    def _var(self, node):
        name = node[1]
        if name in self.context.locals:
            type_name, code = self.context.locals[name]
            return _Typed(code, type_name)
        kind = self.context.variables.get(name)
        if kind is None:
            raise ExpressionError("unknown variable %r" % name)
        type_name = {"number": "num", "text": "text", "bool": "bool"}.get(
            kind, kind
        )
        if type_name not in ("num", "text", "bool"):
            raise ExpressionError("unknown variable type %r for %r" % (kind, name))
        return _Typed('app.var_%s("%s")' % (type_name, name), type_name)

    def _unary(self, node):
        operand = self.visit(node[2])
        if node[1] == "-":
            return _Typed("(-%s)" % self.as_num(operand), "num")
        return _Typed("(!%s)" % self.as_bool(operand), "bool")

    def _bin(self, node):
        operator = node[1]
        left = self.visit(node[2])
        right = self.visit(node[3])
        if operator in ("and", "or"):
            symbol = "&&" if operator == "and" else "||"
            return _Typed(
                "(%s %s %s)" % (self.as_bool(left), symbol, self.as_bool(right)),
                "bool",
            )
        if operator in ("==", "!="):
            function = "equal" if operator == "==" else "not_equal"
            return _Typed(
                "app.%s(%s, %s)" % (function, self.value(left), self.value(right)),
                "bool",
            )
        left_code = self.as_num(left)
        right_code = self.as_num(right)
        if operator == "+":
            return _Typed("(%s + %s)" % (left_code, right_code), "num")
        if operator == "-":
            return _Typed("(%s - %s)" % (left_code, right_code), "num")
        if operator == "*":
            return _Typed("(%s * %s)" % (left_code, right_code), "num")
        if operator == "/":
            return _Typed("(%s / %s)" % (left_code, right_code), "num")
        if operator == "%":
            code = ("std::fmod(%s, %s)" if self.cpp else "(%s %% %s)") % (
                left_code, right_code
            )
            return _Typed(code, "num")
        if operator == "^":
            code = ("std::pow(%s, %s)" if self.cpp
                    else "(%s).powf(%s)") % (left_code, right_code)
            return _Typed(code, "num")
        if operator in ("<", ">", "<=", ">="):
            return _Typed("(%s %s %s)" % (left_code, operator, right_code), "bool")
        raise ExpressionError("unknown operator %r" % operator)

    def _call(self, node):
        name, arguments = node[1], node[2]
        values = [self.visit(argument) for argument in arguments]
        codes = [self.value(value) for value in values]
        numbers = [self.as_num(value) for value in values]
        sprite = self.context.sprite

        simple_cpp = {
            "x position": "app.sprite_x(%s)" % sprite,
            "y position": "app.sprite_y(%s)" % sprite,
            "direction": "app.sprite_direction(%s)" % sprite,
            "costume": "app.sprite_costume(%s)" % sprite,
            "size": "app.sprite_size(%s)" % sprite,
            "timer": "app.timer()",
            "mouse x": "app.mouse_x()",
            "mouse y": "app.mouse_y()",
            "touching edge": "app.touching_edge(%s)" % sprite,
        }
        simple_rust = dict(simple_cpp)  # The generated runtime uses the same API.
        if name in simple_cpp:
            type_name = BUILTINS[name][1]
            return _Typed((simple_cpp if self.cpp else simple_rust)[name], type_name)

        if name == "key pressed":
            key = self._string_literal(arguments[0], name)
            if key not in KEYS:
                raise ExpressionError("unknown key %r" % key)
            return _Typed("app.key_pressed(%d)" % KEYS[key], "bool")
        if name == "touching sprite":
            target = self._string_literal(arguments[0], name)
            try:
                index = list(self.context.sprites).index(target)
            except ValueError:
                raise ExpressionError("unknown sprite %r" % target) from None
            return _Typed("app.touching_sprite(%s, %d)" % (sprite, index), "bool")

        if name == "random":
            return _Typed("app.random_range(%s, %s)" % tuple(numbers), "num")
        if name in ("abs", "sqrt", "sin", "cos", "floor", "ceil", "round"):
            return _Typed("app.%s_num(%s)" % (name, numbers[0]), "num")
        if name == "min":
            code = ("std::min(%s, %s)" if self.cpp
                    else "(%s).min(%s)") % tuple(numbers)
            return _Typed(code, "num")
        if name == "max":
            code = ("std::max(%s, %s)" if self.cpp
                    else "(%s).max(%s)") % tuple(numbers)
            return _Typed(code, "num")
        if name == "len":
            return _Typed("app.length(%s)" % codes[0], "num")
        if name == "to number":
            return _Typed("app.num(%s)" % codes[0], "num")
        if name == "to text":
            return _Typed("app.text(%s)" % codes[0], "text")
        if name == "join":
            return _Typed("app.join(%s, %s)" % tuple(codes), "text")
        raise ExpressionError("unknown function %r" % name)

    @staticmethod
    def _string_literal(node, function):
        if node[0] != "str":
            raise ExpressionError("%s needs a literal text argument" % function)
        return node[1]


def translate_expression(source, context):
    """Translate *source* to C++ or Rust according to *context*."""
    node = parse_expression(source)
    return _Translator(context).visit(node).code
