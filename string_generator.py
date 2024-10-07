import re

from xeger import Xeger

from preprocessor import Preprocessor, ConstraintError

class StringGenerator:
    def __init__(self, limit, seed):
        self.limit = limit
        self.seed = seed
        self.generator = Xeger(limit=limit, seed=seed) # seed for Random module
        self.preprocessor = Preprocessor()
    
    def _get_longest_common_substring(self, strings):
        def __get_n_grams(string: str, n: int) -> set:
            n_grams = set()
            for i in range(0, len(string) - n + 1):
                n_grams.add(string[i : i + n])
            return n_grams

        def __get_all_grams(string: str) -> set:
            all_grams = set()
            for length in range(len(string) + 1):
                n_grams = __get_n_grams(string, length)
                all_grams.update(n_grams)
            return all_grams

        strings_n_grams = set()
        for string in strings:
            all_grams = __get_all_grams(string)
            strings_n_grams.add(frozenset(all_grams))
        intersection = frozenset.intersection(*strings_n_grams)
        longest_common_substring = max(intersection, key=len)
        return longest_common_substring

    def _generate_positive_set(self, regex):
        positive_set = set()
        for i in range(200):
            string = self.generator.xeger(regex)
            if len(string) <= 30:
                # sanity check
                if re.fullmatch(regex, string):
                    positive_set.add(string)
            if len(positive_set) == 10:
                break
        # Don't remove empty string. It is a valid string.
        # .* matches empty string.
        return positive_set

    def _get_substitutions(self, strings, regex):
        # error-prone
        substitutions = dict()
        index = 0
        while True:
            lcs = self._get_longest_common_substring(strings)
            if len(lcs) < 2:
                break
            substitution = chr(index)
            substitutions[substitution] = lcs
            for i in range(len(strings)):
                strings[i] = strings[i].replace(lcs, substitution)
            regex_lcs = ""
            for character in lcs:
                if character in "$()*+./?[\\]^|{}":
                    character = "\\" + character
                regex_lcs += character
            regex = regex.replace(regex_lcs, substitution)
            index += 1
        return regex, strings, substitutions

    def _generate_negative_set(self, regex):
        # regex perturbation
        pass

    def _generate_labels(self, regex, positive_set):

        pass

    def generate_string(self, file_path):
        with open(file_path) as f:
            regexes = f.readlines()

        for i, regex in enumerate(regexes, 1):
            regex = eval(regex)

            if file_path.endswith('snort-clean.re'):
                regex = regex[1 : regex.rfind('/')]
            
            try:
                regex = self.preprocessor.preprocess(regex)
            except ConstraintError:
                continue
            except re.error:
                continue

            positive_set = self._generate_positive_set(regex)

            print(repr(regex), len(regex))
            print(positive_set)

            groups = re.fullmatch(regex, positive_set.pop()).groups()
            #for group in groups:

            substituted_regex, strings, substitutions = self._get_substitutions(positive_set, regex)
            negative_set = self._generate_negative_set(regex)
            label, subregex_list = self._generate_labels(substituted_regex, positive_set)

generator = StringGenerator(10, 10)
generator.generate_string('snort-clean.re')
