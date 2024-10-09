import sre_parse as parser
import sre_constants as constants
from _sre import MAXREPEAT # built-in module
from string import printable

class ConstraintError(Exception):
    pass

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
            'min_repeat': lambda x: self._handle_repeat(*x, is_min=True),
            'max_repeat': lambda x: self._handle_repeat(*x),
            'negate': lambda x: self._handle_negate(x)
        }

    def _is_valid_character(self, character):
        return character in printable

    def _handle_literal(self, value):
        # value: integer
        character = chr(value)
        if not self._is_valid_character(character):
            raise ConstraintError(f'Not a printable ASCII character: {character}')
        if character in self._special_characters:
            if character == '\\':
                return r'\\'
            return '\\' + character
        return character

    def _handle_not_literal(self, value):
        # value: integer
        character = chr(value)
        if not self._is_valid_character(character):
            raise ConstraintError(f'Not a printable ASCII character: {character}')
        return f'[^{character}]'

    def _handle_at(self, value):
        if value == constants.AT_BOUNDARY or value == constants.AT_NON_BOUNDARY:
            raise ConstraintError(f'Zero-width assertion: {value}')
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
            #if len(candidates[i]) == 2 and candidates[i][-1] in self._special_characters:
            #    candidates[i] = candidates[i][-1]
        return f'[{"".join(candidates)}]'

    def _handle_any(self, value):
        # value: None
        return '.'

    def _handle_range(self, value):
        # value: (low, high)
        low, high = chr(value[0]), chr(value[1])
        if not self._is_valid_character(low) or not self._is_valid_character(high):
            raise ConstraintError(f'Not a printable ASCII character range: {low}-{high}')
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
        self._groups[self._n_groups] = len(self.preprocessed_regex) + 1
        self._n_groups += 1
        result = ''.join(self._handle_state(i) for i in value[3])
        return f'({result})'

    def _handle_assert(self, value):
        raise ConstraintError(f'Zero-width assertion: Positive lookaround assertion')

    def _handle_assert_not(self, value):
        raise ConstraintError(f'Zero-width assertion: Negative lookaround assertion')

    def _handle_groupref(self, value):
        # value: integer
        return f'\\{self._groups[value]}'

    def _handle_repeat(self, start_range, end_range, value, is_min=False):
        auxilary = '?' if is_min else ''
        if start_range == 1 and end_range == self._max_repeat:
            operator = '+' + auxilary
        elif start_range == 0 and end_range == self._max_repeat:
            operator = '*' + auxilary
        elif start_range == 0 and end_range == 1:
            operator = '?' + auxilary
        elif start_range == end_range:
            operator = '{%s}' % start_range + auxilary
        else:
            if start_range == 0:
                start_range = ''
            if end_range == self._max_repeat:
                end_range = ''
            operator = '{%s,%s}' % (start_range, end_range) + auxilary
        operand = ''.join(self._handle_state(i) for i in value)
        return operand + operator

    def _handle_negate(self, value):
        # value: None
        return '^'

    def _handle_state(self, state):
        opcode, value = state
        return self._cases[str(opcode).lower()](value)

    def _preprocess(self, parse_tree):
        self.preprocessed_regex = []
        self._groups = {}
        self._n_groups = 1
        is_last_literal = False
        # pre-compute lcs tokenization #
        index = 0
        length = 0
        for state in parse_tree:
            opcode, _ = state
            current_regex = self._handle_state(state)
            if opcode == parser.LITERAL:
                if is_last_literal:
                    self.preprocessed_regex[-1] += current_regex
                else:
                    self.preprocessed_regex.append('(' + current_regex)
                is_last_literal = True
                # pre-compute lcs tokenization #
                length += 1
            else:
                if is_last_literal:
                    self.preprocessed_regex[-1] += ')'
                    # pre-compute lcs tokenization #
                    if length >= 2:
                        self.preprocessed_regex[-1] = f'({chr(index)})'
                        index += 1
                    length = 0
                is_last_literal = False
                if opcode == parser.SUBPATTERN:
                    self.preprocessed_regex.append(current_regex)
                elif opcode == parser.AT:
                    continue
                else:
                    self.preprocessed_regex.append('(' + current_regex + ')')
        if is_last_literal:
            self.preprocessed_regex[-1] += ')'
            # pre-compute lcs tokenization #
            if length >= 2:
                self.preprocessed_regex[-1] = f'({chr(index)})'
                index += 1
            length = 0
        for i in range(len(self.preprocessed_regex)):
            self.preprocessed_regex[i] = f'(?P<t{i + 1}>' + self.preprocessed_regex[i][1:]
        regex_string = ''.join(self.preprocessed_regex)
        regex_list = self.preprocessed_regex
        return regex_string, regex_list

    def preprocess(self, regex):
        parse_tree = parser.parse(regex)
        regex_string, regex_list = self._preprocess(parse_tree)
        return regex_string, regex_list

if __name__ == '__main__':
    import unittest
    class TestPreprocessor(unittest.TestCase):
        def test_preprocessor(self):
            test_cases = [
                # snort-clean.re
                ('filename=[^\n]*\\x2ecov', '(?P<g1>\x00)(?P<g2>[^\n]*)(?P<g3>\x01)'),
                ('\\x2eswf([\\x3f\\x2f]|$)', '(?P<g1>\x00)(?P<g2>[?/]|)'),
                # ('\\d+&', '(?P<1>\\d+)(?P<2>&)'),
                # ('^die\\x7c\\d+\\x7c\\d+\\x7C[a-z0-9]+\\x2E[a-z]{2,3}\\x7C[a-z0-9]+\\x7C', '(?P<1>\x00)(?P<2>\\d+)(?P<3>\\|)(?P<4>\\d+)(?P<5>\\|)(?P<6>[a-z0-9]+)(?P<7>\\.)(?P<8>[a-z]{2,3})(?P<9>\\|)(?P<10>[a-z0-9]+)(?P<11>\\|)'),
                # ('\\/[a-z0-9]{12}\\.txt$', '(?P<1>/)(?P<2>[a-z0-9]{12})(?P<3>\x00)'),
                ('([\\x2f\\x5c]|%2f|%5c)', '(?P<t1>[/\\\\]|%2f|%5c)'),
                #('filename\\s*?=\\s*?[\\x22\\x27]?[^\r\n]*?(\\x2e|%2e){2}([\\x2f\\x5c]|%2f|%5c)', '(?P<t1>\x00)(?P<t2>\\s*?)(?P<t3>=)(?P<t4>\\s*?)(?P<t5>["\']?)(?P<t6>[^\r\n]*?)(?P<t7>(\\.|%2e){2})(?P<t8>[/\\\\]|%2f|%5c)'),
                # regexlib-clean.re
                # ERROR: sre_parse ignores non-capturing groups
                #('(?:\\?=.*)?$', '((\\?=.*)?)'),
                # Not separating the groups; not error necessarily
                # ('(^\\-?[0-9]*\\.?[0-9]+$)', '(?P<1>-?[0-9]*\\.?[0-9]+)'),
                # corpusPatterns.txt
                # ('(.).\\1', '(?P<1>.)(?P<2>.)(?P<3>\\1)'),
                # ('(?P<delim>[^\\w\n"\'])(?P<space> ?)(?P<quote>["\']).*?(?P=quote)(?P=delim)', '(?P<1>[^\\w\n"\'])(?P<2> ?)(?P<3>["\'])(?P<4>.*?)(?P<5>\\3)(?P<6>\\1)'),
                # ('src=([\\\'"])(.+?)\\1', '(?P<1>\x00)(?P<2>[\'"])(?P<3>.+?)(?P<4>\\2)'),
                # ('%module(\\s*\\(.*\\))?\\s+("?)(.+)\\2', '(?P<1>\x00)(?P<2>(\\s*\\(.*\\))?)(?P<3>\\s+)(?P<4>"?)(?P<5>.+)(?P<6>\\4)'),
                # ERROR: can't handle subgroups
                # ('(a(b)c)d')
                # group 1: (a(b)c)
                # gropu 2: (b)
                # Groups can be nested; to determine the number, just count the opening parenthesis characters, going from left to right.
                # ('(g(s))\\1\\2', '(?P<1>g(s))(?P<2>\\1)(?P<3>\\2)')
            ]
            preprocessor = Preprocessor()
            for regex, expected_output in test_cases:
                with self.subTest(regex=regex):
                    regex_string, regex_list = preprocessor.preprocess(regex)
                    self.assertEqual(regex_string, expected_output)
    unittest.main()
