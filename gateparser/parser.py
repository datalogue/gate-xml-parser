import os
from collections import defaultdict, Counter

from xmltodict import parse

import spacy
from glom import glom
import warnings
from pprint import pprint

from json import JSONDecodeError
from spacy.tokenizer import Tokenizer

nlp = spacy.load('en')



class GateBIOParser(object):
    def __init__(self, filename, language='english',
                                 encoding='windows-1252',
                                 annotation_spec='GateDocument.AnnotationSet',
                                 node_spec='GateDocument.TextWithNodes',
                                 text_spec='GateDocument.TextWithNodes'):
        self.filename = filename
        self._encoding = encoding
        self._annotation_spec = annotation_spec
        self.language = language
        self._node_spec = node_spec
        self._text_spec = text_spec
        self.annotations, self.nodes, self.text = self.load_xml()
        self.BIO = self._tag_bio()



    def load_xml(self):
        if not '.xml' in self.filename:
            raise ValueError('File must be XML (exported from GATE)')

        with open(self.filename, 'rt', encoding=self._encoding) as xml:
            annotations = parse(xml.read(), strip_whitespace=False)
            parsed_annos = glom(annotations, self._annotation_spec)

            if parsed_annos is not None:
                if isinstance(parsed_annos, list):
                    # Handle if more than one Annotation Set -> in our data, the second one had labels
                    annos = parsed_annos[0]
                    if isinstance(annos, str):
                        parsed_annos = parsed_annos[1]
                        if 'Annotation' in parsed_annos:
                            annos = parsed_annos['Annotation']
                        else:
                            annos = parsed_annos = None
                    else:
                        annos = annos['Annotation']

                elif isinstance(parsed_annos, str) and not bool(parsed_annos.strip()):
                    annos = parsed_annos = None
                else:
                    annos = parsed_annos['Annotation']
            else:
                annos = parsed_annos = None

            if annos is not None and glom(annotations, self._text_spec) is None:
                raise ValueError('Error in Annotation File. No Annotations, but Nodes are present.')

            nodes = glom(annotations, self._node_spec)

            if annos is not None and nodes is not None:
                nodes = nodes['Node']

            if annos is not None and nodes is not None:
                text = glom(annotations, self._text_spec)['#text']


            else:
                # warnings.warn(f'No Text to Annotate in {self.filename}')
                text = None


        return annos, nodes, text


    def _tag_bio(self):
        annos, nodes, text = self.annotations, self.nodes, self.text
        if not nodes or not text:
            return None
        if not annos:
            sentences, _, _ = self._tokenize_sentences()
            empty_out = [{'tokens': tokens,'labels': ['O'] * len(tokens)} for tokens in sentences]
            return empty_out
        elif isinstance(annos, list):
           # handle many annos
            annos = {(a['@StartNode'], a['@EndNode']): a['@Type'] for a in annos}
        else:
            annos = { (annos['@StartNode'], annos['@EndNode']): annos['@Type'] }

        entity_indices = annos.keys()

        def create_custom_tokenizer(nlp):
            custom_prefixes = ['/', '\->']
            all_prefixes_re = spacy.util.compile_prefix_regex(tuple(list(nlp.Defaults.prefixes) + custom_prefixes))

            custom_infixes = ['\+', '\(', '\&', '\.', '\,', '\)', '\?', '\->', '\-', '\[', '\]']
            infix_re = spacy.util.compile_infix_regex(tuple(list(nlp.Defaults.infixes) + custom_infixes))

            suffix_re = spacy.util.compile_suffix_regex(nlp.Defaults.suffixes)

            return Tokenizer(nlp.vocab, nlp.Defaults.tokenizer_exceptions,
                             prefix_search = all_prefixes_re.search,
                             infix_finditer = infix_re.finditer, suffix_search = suffix_re.search,
                             token_match=None)


        nlp.tokenizer = create_custom_tokenizer(nlp)

        doc = nlp(text, disable=['ner'])

        tokens, labels = [str(t) for t in list(doc)], ['O'] * len(doc)
        token_char_starts = [str(doc[i:i+1].start_char) for i in range(len(tokens))]
        token_char_ends = [str(doc[i:i+1].end_char - 1) for i in range(len(tokens))]

        ws = [self.text[int(i):int(j)].strip() for i,j in entity_indices]

        for entity_index, (start, end) in enumerate(entity_indices):
            char_start_idx = -1

            if start in token_char_starts:
                char_start_idx = start
                adjustment = 0
            elif str(int(start) - 1) in token_char_starts:
                char_start_idx = str(int(start) - 1)
                adjustment = 1
            elif str(int(start) + 1) in token_char_starts:
                char_start_idx = str(int(start) + 1)
                adjustment = 1

            if char_start_idx == -1:
                raise ValueError('Char Start not set')

            token_start_idx = token_char_starts.index(char_start_idx)
            token_end_idx = token_start_idx


            while True:
                try:
                    if int(end) <= int(token_char_ends[token_end_idx]):
                        break
                    token_end_idx += 1
                except IndexError as e:
                    if int(end) - 1  <= int(token_char_ends[token_end_idx-1]):
                        token_end_idx -= 1
                        break
                    else:
                        raise ValueError('LooP BrokE')


            else:
                raise ValueError('-- start found but not end -- ')


            if (start, end) not in annos:
                raise ValueError('Parse Error!')


            label = annos[(start, end)]

            if label == 'UserIDWindows':
                label = 'UserIDGeneric'
            elif label in ('LastName', 'FirstName'):
                label = 'FullName'
            elif label in ('Email', 'JobTitle'):
                continue

            if token_start_idx < token_end_idx:
                for i in range(int(token_start_idx), int(token_end_idx)):
                    if tokens[i] in ',)(':
                        continue
                    else:
                        if tokens[i]:
                            labels[i] = 'I-' + label
                if ' ' in ws[entity_index] and label not in ('UserIDGeneric', 'Organisation'):
                    if int(token_end_idx) - int(token_start_idx) > 1:
                        if all(labels[i] == 'I-' + label for i in range(int(token_start_idx), int(token_end_idx))):
                               labels[token_start_idx] = 'B-' + label

            elif token_start_idx > token_end_idx:
                raise ValueError('Indices are incorrect')
            else:
                labels[token_start_idx] = 'I-' + label

        return {'tokens': tokens, 'labels': labels}



    def get_class_counts(self):
        classes = set(self.BIO['labels'])
        counts = Counter(self.BIO['labels'])
        return counts


    def print_class_counts(self):
        class_counts = self.get_class_counts()
        print('Sample Counts')
        for tag in class_counts:
            print(tag, ':', class_counts[tag])
