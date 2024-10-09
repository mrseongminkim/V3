import re
import random

from xeger import Xeger
from datasets import Dataset
from tqdm import tqdm

from preprocessor import Preprocessor, ConstraintError

class StringGenerator:
    def __init__(self, limit, seed, max_n_strings, max_length):
        self.limit = limit
        self.seed = seed
        self.max_n_strings = max_n_strings
        self.max_length = max_length
        self.generator = Xeger(limit=limit, seed=seed) # seed for Random module
        self.preprocessor = Preprocessor()
        self.max_search = 200

    def _generate_positive_strings(self, regex_string):
        positive_strings = set()
        for _ in range(self.max_search):
            try:
                string = self.generator.xeger(regex_string)
            except Exception as e:
                print(e)
                print(repr(regex_string))
                print(repr(regex_string)[94:96])
            if len(string) <= self.max_length and re.fullmatch(regex_string, string):
                positive_strings.add(string)
                if len(positive_strings) == self.max_n_strings:
                    break
        return list(positive_strings)

    def _generate_negative_strings(self, regex_string, positive_strings):
        # symbol level perturbation
        # regex level perturbation -> (T_1)([^\r\n])(T_2) -> (T_1)([\r\n](T_2))
        negative_strings = set()
        if not re.fullmatch(regex_string, ''):
            negative_strings.add('')
        alphabet = set()
        for string in positive_strings:
            alphabet.update(set(string))
        alphabet = list(alphabet)
        for _ in range(self.max_search):
            string = positive_strings[random.randint(0, len(positive_strings) - 1)]
            n_perturbation = len(string) // 5
            for _ in range(n_perturbation):
                index = random.randint(0, len(string) - 1)
                character = alphabet[random.randint(0, len(alphabet) - 1)]
                string = string[:index] + character + string[index + 1:]
            if len(string) <= self.max_length and not re.fullmatch(regex_string, string):
                negative_strings.add(string)
                if len(negative_strings) == self.max_n_strings:
                    break
        return list(negative_strings)

    def _generate_labels(self, regex_string, regex_list, positive_strings):
        labels = []
        for string in positive_strings:
            label = ''
            subregex_group = re.fullmatch(regex_string, string).groupdict()
            for i in range(len(regex_list)):
                if regex_list[i] in [".*", "\d*", "\w*", "(.)*", "(\d)*", "(\w)*", "(.*)", "(\d*)", "(\w*)", ".*?", "\d*?", "\w*?"]:
                    label += len(subregex_group[f't{i + 1}']) * '0'
                else:
                    # Constraint: Only supports maximum 9 subregexes
                    label += len(subregex_group[f't{i + 1}']) * str(i + 1)
            labels.append(label)
        return labels

    def generate_string(self, file_path):
        with open(file_path) as f:
            regexes = f.readlines()

        if file_path.endswith('snort-clean.re'):
            save_location = 'data/neural_splitter/snort'
            dataset_specific_postprocess = lambda x: x[1 : x.rfind('/')]

        data = {'positive_strings': [], 'labels': []}

        for i, regex in enumerate(tqdm(regexes), 1):
            regex = eval(regex)

            if file_path.endswith('snort-clean.re'):
                regex = dataset_specific_postprocess(regex)

            try:
                regex_string, regex_list = self.preprocessor.preprocess(regex)
            except ConstraintError:
                continue
            except re.error:
                continue

            positive_strings = self._generate_positive_strings(regex_string)
            #negative_strings = self._generate_negative_strings(regex_string, positive_strings)
            labels = self._generate_labels(regex_string, regex_list, positive_strings)

            data['positive_strings'].append(positive_strings)
            data['labels'].append(labels)
        
        dataset = Dataset.from_dict(data)
        dataset.save_to_disk(save_location)

generator = StringGenerator(limit=5, seed=10, max_n_strings=10, max_length=10)
generator.generate_string('data/automatark/snort-clean.re')

    # def __get_longest_common_substring(self, strings):
    #     def __get_n_grams(string: str, n: int) -> set:
    #         n_grams = set()
    #         for i in range(0, len(string) - n + 1):
    #             n_grams.add(string[i : i + n])
    #         return n_grams

    #     def __get_all_grams(string: str) -> set:
    #         all_grams = set()
    #         for length in range(len(string) + 1):
    #             n_grams = __get_n_grams(string, length)
    #             all_grams.update(n_grams)
    #         return all_grams

    #     strings_n_grams = set()
    #     for string in strings:
    #         all_grams = __get_all_grams(string)
    #         strings_n_grams.add(frozenset(all_grams))
    #     intersection = frozenset.intersection(*strings_n_grams)
    #     longest_common_substring = max(intersection, key=len)
    #     return longest_common_substring

    # def _substitute_longest_common_substrings(self, regex, positive_strings):
    #     substitution_map = dict()
    #     index = 0
    #     while True:
    #         lcs = self.__get_longest_common_substring(positive_strings)
    #         if len(lcs) < 2:
    #             break
    #         lcs_token = chr(index)
    #         index += 1
    #         substitution_map[lcs_token] = lcs
    #         for i in range(len(positive_strings)):
    #             positive_strings[i] = positive_strings[i].replace(lcs, lcs_token)
            
    #         exit()

    #         regex_lcs = ""
    #         for character in lcs:
    #             if character in "$()*+./?[\\]^|{}":
    #                 character = "\\" + character
    #             regex_lcs += character
    #         regex = regex.replace(regex_lcs, substitution)
    #     return regex, positive_strings, substitution_map
