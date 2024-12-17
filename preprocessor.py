import string
import sre_parse as parser
import sre_constants as constants
from _sre import MAXREPEAT # type: ignore
from string import printable

class ConstraintError(Exception):
    pass

class Preprocessor:
    def __init__(self):
        self._max_repeat = MAXREPEAT
        self._special_characters = r'.^$*+?\\[|()'
        self._categories = {
            'category_digit': r'\d',
            'category_word': r'\w',
            'category_space': ' ',
            'category_not_word': r'\W',
            'category_not_digit': r'\D',
            'category_not_space': r'\S',
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
        '''
        0. if character is not a printable ASCII character, raise an error
        1. if character is a whitespace character, return ' '
        2. if character is a special character, return '\\' + character
        3. otherwise, return character
        value: integer
        '''
        character = chr(value)
        if not self._is_valid_character(character):
            raise ConstraintError(f'Not a printable ASCII character: {character}')
        if character in string.whitespace:
            return ' '
        if character in self._special_characters:
            if character == '\\':
                return r'\\'
            return '\\' + character
        return character

    def _handle_not_literal(self, value):
        raise ConstraintError(f'Can\'t handle negation')
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
        '''
        0. if it's character class, return the character class without enclosing brackets
        1. if it's negated character class, raise ConstraintError
        value: list of states
        '''
        candidates = [self._handle_state(i) for i in value]
        # Named character classes
        if len(candidates) == 1 and candidates[0] in self._categories.values():
            return candidates[0]
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
        category = self._categories[str(value).lower()]
        if category in (r'\D', r'\W', r'\S'):
            raise ConstraintError(f'Negated character class: {category}')
        return category

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
        # do not support possessive quantifiers
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
        raise ConstraintError(f'Negation: ^')
        return '^'

    def _handle_state(self, state):
        opcode, value = state
        return self._cases[str(opcode).lower()](value)

    def _preprocess(self, parse_tree):
        self.preprocessed_regex = []
        self._groups = {}
        self._n_groups = 1
        is_last_literal = False
        # pre-compute ground-truth lcs tokenization #
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
        if len(self.preprocessed_regex) > 12:
            raise ConstraintError('Number of subregexes exceeds the limit')
        for i in range(len(self.preprocessed_regex)):
            self.preprocessed_regex[i] = f'(?P<g{i + 1}>' + self.preprocessed_regex[i][1:]
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
                # ('filename=[^\n]*\\x2ecov', '(?P<g1>\x00)(?P<g2>[^\n]*)(?P<g3>\x01)'),
                # ('\\x2eswf([\\x3f\\x2f]|$)', '(?P<g1>\x00)(?P<g2>[\?/]|)'),
                # ('\\d+&', '(?P<g1>\\d+)(?P<g2>&)'),
                # ('\\/[a-z0-9]{12}\\.txt$', '(?P<g1>/)(?P<g2>[a-z0-9]{12})(?P<g3>\x00)'),
                # ('([\\x2f\\x5c]|%2f|%5c)', '(?P<g1>[/\\\\]|%2f|%5c)'),
                # ('filename\\s*?=\\s*?[\\x22\\x27]?[^\r\n]*?(\\x2e|%2e){2}([\\x2f\\x5c]|%2f|%5c)', '(?P<g1>\x00)(?P<g2> *?)(?P<g3>=)(?P<g4> *?)(?P<g5>["\']?)(?P<g6>[^  ]*?)(?P<g7>(\\.|%2e){2})(?P<g8>[/\\\\]|%2f|%5c)'),

                # regexlib-clean.re
                # ERROR: sre_parse ignores non-capturing groups
                #('(?:\\?=.*)?$', '((\\?=.*)?)'),
                # Not separating the groups; not error necessarily
                # ('(^\\-?[0-9]*\\.?[0-9]+$)', '(?P<1>-?[0-9]*\\.?[0-9]+)'),
                
                # corpusPatterns.txt
                ('([A-Z]+)([A-Z][a-z])', '(?P<g1>[A-Z]+)(?P<g2>[A-Z][a-z])'),
                ('<!-- REPORTPROBLEM (.*?)-->', '(?P<g1>\x00)(?P<g2>.*?)(?P<g3>\x01)'),
                ('Funcname|Classless_Function', '(?P<g1>Funcname|Classless_Function)'),
                ('[A-Z]+', '(?P<g1>[A-Z]+)'),
                ('\\.php$', '(?P<g1>\x00)'),
                ('\\s+(\\r?\\n)$', '(?P<g1> +)(?P<g2> ? )'),
                ('^(?P<major>\\d+)\\.(?P<minor>\\d+)(\\.(?P<subminor>\\d+))?', '(?P<g1>\\d+)(?P<g2>\\.)(?P<g3>\\d+)(?P<g4>(\\.(\\d+))?)'),
                ('^Accession Number:', '(?P<g1>\x00)'),
                ('^\\s*(\\w+)\\s*:', '(?P<g1> *)(?P<g2>\\w+)(?P<g3> *)(?P<g4>:)'),
                ('src=([\\\'"])(.+?)\\1', '(?P<g1>\x00)(?P<g2>[\'"])(?P<g3>.+?)(?P<g4>\\2)'),
            ]
            preprocessor = Preprocessor()
            for regex, expected_output in test_cases:
                with self.subTest(regex=regex):
                    regex_string, regex_list = preprocessor.preprocess(regex)
                    self.assertEqual(regex_string, expected_output)
    unittest.main()
