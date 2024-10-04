import sre_parse as parser
import sre_constants as constants
from _sre import MAXREPEAT
from string import printable

class Preprocessor:
    def __init__(self):
        self._max_repeat = MAXREPEAT
        self._special_characters = r'.^$*+?\\[|()'
        self._categories = {
            "category_digit": r'\d',
            "category_not_digit": r'\D',
            "category_space": r'\s',
            "category_not_space": r'\S',
            "category_word": r'\w',
            "category_not_word": r'\W',
        }
        self._cases = {
            'literal': lambda x: self._handle_literal(x),
            'not_literal': lambda x: self._handle_not_literal(x),
            'at': lambda x: self._handle_at(x),
            'in': lambda x: self._handle_in(x),
            'any': lambda x: self._handle_any(x),
            'range': lambda x: self._handle_range(x),
            'category': lambda x: self._handle_category(x),
            'branch': lambda x: self._handle_branch(x[1]),
            'subpattern': lambda x: self._handle_subpattern(x),
            'assert': lambda x: self._handle_assert(x),
            'assert_not': lambda x: self._handle_assert_not(x),
            'groupref': lambda x: self._handle_groupref(x),
            'min_repeat': lambda x: self._handle_min_repeat(*x),
            'max_repeat': lambda x: self._handle_max_repeat(*x),
            'negate': lambda x: self._handle_negate(x)
        }
    
    def _is_valid_character(self, character):
        return character in printable

    def _handle_literal(self, value):
        # value: integer
        character = chr(value)
        if not self._is_valid_character(character):
            raise ValueError(f'Not a printable ASCII character: {character}')
        if character in self._special_characters:
            return '\\' + character
        return character

    def _handle_not_literal(self, value):
        # value: integer
        character = chr(value)
        if not self._is_valid_character(character):
            raise ValueError(f'Not a printable ASCII character: {character}')
        return f'[^{character}]'

    def _handle_at(self, value):
        if value == constants.AT_BOUNDARY or value == constants.AT_NON_BOUNDARY:
            raise ValueError(f'Zero-width assertion: {value}')
        return ''

    def _handle_in(self, value):
        # value: list of states
        candidates = [self._handle_state(i) for i in value]
        # Named character classes
        if len(candidates) == 1 and candidates[0] in self._categories.values():
            return candidates[0]
        for i in range(len(candidates)):
            # Doesn't escape '-' and ']' if they are at the beginning or end of the character class
            if (candidates[i] == '-' or candidates[i] == ']') and 0 < i and i < len(candidates) - 1:
                candidates[i] = '\\' + candidates[i]
            if len(candidates[i]) == 2 and candidates[i][-1] in self._special_characters:
                candidates[i] = candidates[i][-1]
        return f'[{"".join(candidates)}]'

    def _handle_any(self, value):
        # value: None
        return '.'

    def _handle_range(self, value):
        # value: (low, high)
        low, high = chr(value[0]), chr(value[1])
        if not self._is_valid_character(low) or not self._is_valid_character(high):
            raise ValueError(f'Not a printable ASCII character range: {low}-{high}')
        return f'{low}-{high}'
    
    def _handle_category(self, value):
        # value: category
        return self._categories[str(value).lower()]

    def _handle_branch(self, value):
        # value: list of list of states
        regexes = []
        for states in value:
            regex = ''
            for state in states:
                regex += self._handle_state(state)
            regexes.append(regex)
        return '|'.join(regexes)

    def _handle_subpattern(self, value):
        # value: group, add_flags, del_flags, pattern
        result = ''.join(self._handle_state(i) for i in value[3])
        return f'({result})'

    def _handle_assert(self, value):
        # value: lookaround, pattern
        lookaround = '=' if value[0] == 1 else '<='
        regex = []
        for state in value[1]:
            regex.append(self._handle_state(state))
        return f'(?{lookaround}' + ''.join(regex) + ')'

    def _handle_assert_not(self, value):
        # value: lookaround, pattern
        lookaround = '!' if value[0] == 1 else '<!'
        regex = []
        for state in value[1]:
            regex.append(self._handle_state(state))
        return f'(?{lookaround}' + ''.join(regex) + ')'

    def _handle_groupref(self, value):
        # value: integer
        return f'\\{value}'

    def _handle_min_repeat(self, start_range, end_range, value):
        if start_range == 1 and end_range == self._max_repeat:
            operator = '+?'
        elif start_range == 0 and end_range == self._max_repeat:
            operator = '*?'
        elif start_range == 0 and end_range == 1:
            operator = '??'
        elif start_range == end_range:
            operator = '{%s}?' % start_range
        else:
            if start_range == 0:
                start_range = ''
            if end_range == self._max_repeat:
                end_range = ''
            operator = '{%s,%s}?' % (start_range, end_range)
        operand = ''.join(self._handle_state(i) for i in value)
        return operand + operator

    def _handle_max_repeat(self, start_range, end_range, value):
        if start_range == 1 and end_range == self._max_repeat:
            operator = '+'
        elif start_range == 0 and end_range == self._max_repeat:
            operator = '*'
        elif start_range == 0 and end_range == 1:
            operator = '?'
        elif start_range == end_range:
            operator = '{%s}' % start_range
        else:
            if start_range == 0:
                start_range = ''
            if end_range == self._max_repeat:
                end_range = ''
            operator = '{%s,%s}' % (start_range, end_range)
        operand = ''.join(self._handle_state(i) for i in value)
        return operand + operator

    def _handle_negate(self, value):
        # value: None
        return '^'

    def _handle_state(self, state):
        opcode, value = state
        return self._cases[str(opcode).lower()](value)

    def _preprocess(self, parse_tree):
        preprocessed_regex = []
        for state in parse_tree:
            print(state)
            preprocessed_regex.append(self._handle_state(state))
        return ''.join(preprocessed_regex)

    def preprocess(self, regex):
        parse_tree = parser.parse(regex)
        #print(parse_tree)
        result = self._preprocess(parse_tree)
        return result
