def collect_grouped_strings(positive_set, labels):
    # split_size
    # is_last_sigma
    unique_labels = sorted(set(label for sublist in labels for label in sublist if label != '<pad>'))
    
    # Initialize a dictionary of lists for each group
    groups = {label: ['' for _ in positive_set] for label in unique_labels}

    # Process each string in the positive_set and assign characters based on labels
    for i, string in enumerate(positive_set):
        for j, char in enumerate(string):
            label = labels[i][j]  # Get the corresponding label for the character
            if label == '<pad>':
                break
            elif label == 0:
                # handle sigma
                pass
            else:
                groups[label][i] += char

    # Convert the dictionary to a list of lists ordered by labels
    output = [groups[label] for label in unique_labels]

    return output

if __name__ == '__main__':
    import unittest
    class TestSplit(unittest.TestCase):
        def test_split(self):
            test_cases = [
                (
                    ['abc', 'aabc', 'bc'],
                    [[1, 2, 3, '<pad>'], [1, 1, 2, 3], [2, 3, '<pad>', '<pad>']],
                    [['a', 'aa', ''], ['b', 'b', 'b'], ['c', 'c', 'c']]
                ),
            ]
            for positive_set, labels, expected_output in test_cases:
                with self.subTest(positive_set=positive_set, labels=labels):
                    output = collect_grouped_strings(positive_set, labels)
                    self.assertEqual(output, expected_output)
    unittest.main()
