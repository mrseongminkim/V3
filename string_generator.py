import re
import string

from xeger import Xeger
from datasets import Dataset
from tqdm import tqdm

from preprocessor import Preprocessor, ConstraintError

class StringGenerator:
    '''
    limit: int; maximum number of repetitions
    seed: int; seed for random module
    max_n_strings: int; maximum number of strings to generate
    max_length: int; maximum length of string to generate
    max_search: int; maximum number of search for positive and negative strings
    '''
    def __init__(self, limit, seed, max_n_strings, max_length, max_search=200):
        self.limit = limit
        self.seed = seed
        self.max_n_strings = max_n_strings
        self.max_length = max_length
        self.max_search = max_search
        self.preprocessor = Preprocessor()
        self.generator = Xeger(limit=limit, seed=seed) # Xeger internally uses random.seed(seed) so we don't need to set it again
        self.special_subregexes = self._get_special_subregexes()
    
    def _get_special_subregexes(self):
        special_subregexes = []
        named_character_classes = ['.', '\d', '\w']
        for named_character_class in named_character_classes:
            special_subregexes.append(named_character_class + '*')
            special_subregexes.append(named_character_class + '+')
            special_subregexes.append(named_character_class + '?')
            special_subregexes.append(named_character_class + '*?')
            special_subregexes.append(named_character_class + '+?')
            special_subregexes.append(named_character_class + '??')
            
            named_character_class = '(' + named_character_class + ')'
            special_subregexes.append(named_character_class + '*')
            special_subregexes.append(named_character_class + '+')
            special_subregexes.append(named_character_class + '?')

            special_subregexes.append(named_character_class + '*?')
            special_subregexes.append(named_character_class + '+?')
            special_subregexes.append(named_character_class + '??')
        return special_subregexes

    def _substitute_whitespace(self, generated_string):
        for whitespace in string.whitespace:
            generated_string = generated_string.replace(whitespace, ' ')
        return generated_string

    def _generate_positive_strings(self, regex_string):
        positive_strings = set()
        for _ in range(self.max_search):
            try:
                generated_string = self.generator.xeger(regex_string)
            except Exception as e:
                print(e)
                print('Xeger failed to generate string')
                breakpoint()
            if generated_string and len(generated_string) <= self.max_length and re.fullmatch(regex_string, generated_string):
                original_string = generated_string
                generated_string = self._substitute_whitespace(generated_string)
                if not re.fullmatch(regex_string, generated_string):
                    print('original: ', repr(original_string))
                    print('generated:', repr(generated_string))
                    print('regex: ', repr(regex_string))
                    breakpoint()
                positive_strings.add(generated_string)
                if len(positive_strings) == self.max_n_strings:
                    break
        return list(positive_strings)

    # def _generate_negative_strings(self, regex_string, positive_strings):
    #     # symbol level perturbation
    #     # regex level perturbation -> (T_1)([^\r\n])(T_2) -> (T_1)([\r\n](T_2))
    #     negative_strings = set()
    #     if not re.fullmatch(regex_string, ''):
    #         negative_strings.add('')
    #     alphabet = set()
    #     for positive_string in positive_strings:
    #         alphabet.update(set(positive_string))
    #     alphabet = list(alphabet)
    #     for _ in range(self.max_search):
    #         string = positive_strings[random.randint(0, len(positive_strings) - 1)]
    #         n_perturbation = len(string) // 5
    #         for _ in range(n_perturbation):
    #             index = random.randint(0, len(string) - 1)
    #             character = alphabet[random.randint(0, len(alphabet) - 1)]
    #             string = string[:index] + character + string[index + 1:]
    #         if len(string) <= self.max_length and not re.fullmatch(regex_string, string):
    #             negative_strings.add(string)
    #             if len(negative_strings) == self.max_n_strings:
    #                 break
    #     return list(negative_strings)

    def _generate_labels(self, regex_string, regex_list, positive_strings):
        labels = []
        for positive_string in positive_strings:
            label = ''
            try:
                print(repr(positive_string))
                subregex_group = re.fullmatch(regex_string, positive_string).groupdict()
            except:
                breakpoint()
            for i in range(len(regex_list)):
                subregex = regex_list[i][regex_list[i].find('>') + 1 : -1]
                if subregex in self.special_subregexes:
                    label += len(subregex_group[f'g{i + 1}']) * '0'
                else:
                    # Constraint: Only supports maximum 9 subregexes
                    label += len(subregex_group[f'g{i + 1}']) * str(i + 1)
            labels.append(label)
        return labels

    def generate_string(self, file_path):
        with open(file_path) as f:
            regexes = f.readlines()

        if file_path.endswith('snort-clean.re'):
            save_location = 'data/neural_splitter/snort'
            dataset_specific_postprocess = lambda x: x[1 : x.rfind('/')]
        elif file_path.endswith('corpusPatterns.txt'):
            save_location = 'data/neural_splitter/tour_de_source'
            dataset_specific_postprocess = lambda x: x

        data = {'positive_strings': [], 'labels': []}

        for _, regex in enumerate(tqdm(regexes), 1):
            regex = eval(regex)
            regex = dataset_specific_postprocess(regex)

            try:
                regex_string, regex_list = self.preprocessor.preprocess(regex)
            except ConstraintError:
                continue
            except re.error:
                continue

            positive_strings = self._generate_positive_strings(regex_string)
            # empty is not good
            if not positive_strings:
                continue
            #negative_strings = self._generate_negative_strings(regex_string, positive_strings)

            labels = self._generate_labels(regex_string, regex_list, positive_strings)

            data['positive_strings'].append(positive_strings)
            data['labels'].append(labels)

        dataset = Dataset.from_dict(data)
        dataset.save_to_disk(save_location)

'''
list of files to generate strings from:
data/automatark/snort-clean.re
data/automatark/regexlib-clean.re
data/tour_de_source/corpusPatterns.txt
'''
generator = StringGenerator(limit=5, seed=0, max_n_strings=10, max_length=15)
generator.generate_string(file_path='data/tour_de_source/corpusPatterns.txt')
