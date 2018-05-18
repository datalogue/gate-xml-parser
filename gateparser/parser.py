
import os
from collections import defaultdict, Counter

from xmltodict import parse
from nltk.tokenize import sent_tokenize, word_tokenize
from glom import glom
import warnings

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
        self.labels = self.labels()


    def labels(self):
        if self.BIO is None:
            return None
        return [sentence['labels'] for sentence in self.BIO]

    def load_xml(self):
        if not '.xml' in self.filename:
            raise ValueError('File must be XML (exported from GATE)')

        with open(self.filename, 'rt', encoding=self._encoding) as xml:
            annotations = parse(xml.read())
            parsed_annos = glom(annotations, self._annotation_spec)

            if parsed_annos is not None:
                if isinstance(parsed_annos, list):
                    annos = parsed_annos[0]['Annotation']
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
                warnings.warn(f'No Text to Annotate in {self.filename}')
                text = None

        return annos, nodes, text

    def _tokenize_sentences(self):
        sentences = sent_tokenize(self.text, language=self.language)

        # Where you would call NP_Chunks from spacy
        # print(sentences)

        sentence_words = [word_tokenize(s) for s in sentences]
        # get sentence end indices
        sentence_end_chars = []
        current_char_count = 0

        for s in sentences:
            current_char_count += len(s) + 1
            sentence_end_chars.append(current_char_count)
        return sentences, sentence_words, sentence_end_chars

    def _process_char_indices_to_words(self):
        entity_indices =  [(self.nodes[i]['@id'], self.nodes[i+1]['@id'])
                            for i in range(0, len(self.nodes)-1, 2)]
        return entity_indices, [self.text[int(i)-1:int(j)-1] for i,j in entity_indices]

    def _char_idxs_to_sentence_idx(self, entity_indices, sentence_end_chars):
        sl_wx = {}
        for i,j in entity_indices:
            word = self.text[int(i)-1:int(j)-1]
            for idx, sentence_end_idx in enumerate(sorted(sentence_end_chars)):
                if int(j) <= sentence_end_idx:
                    sl_wx[(i,j)] = idx
                    break
            else:
                # todo fix
                sl_wx[(i,j)] = idx
        return sl_wx

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

        entity_indices, ws = self._process_char_indices_to_words()

        sentences, sentence_words, sentence_end_chars = self._tokenize_sentences()
        sl_wx = self._char_idxs_to_sentence_idx(entity_indices, sentence_end_chars)


        target_word_per_sentence = defaultdict(list)
        for (char_start,char_end), sent_idx in sl_wx.items():
            target_word_per_sentence[sent_idx].append((char_start, char_end))

        sentence_to_ws = defaultdict(list)
        for i,j in entity_indices:
            sentence_to_ws[sl_wx[(i,j)]].append(text[int(i)-1:int(j)-1])

        sentence_labels = {}
        for sentence_idx, word_indices in target_word_per_sentence.items():
            labels = []
            for target_word in sentence_to_ws[sentence_idx]:
                if ' ' in target_word:
                    tgts = target_word.split(' ')
                    span = len(tgts)
                    # for through each n-len sequence
                    for i in range(len(sentence_words[sentence_idx])):
                        candidate = ' '.join(sentence_words[sentence_idx][i:i+span])
                        if candidate == target_word:
                            labels.append(((i, i+span), annos[entity_indices[ws.index(candidate)]]))

                else:
                    for idx, word in enumerate(sentence_words[sentence_idx]):
                            if word == target_word:
                                labels.append((idx, annos[entity_indices[ws.index(word)]]))

            sentence_labels[sentence_idx] = labels



        outputs = []
        for sent_idx, labels in sentence_labels.items():
            tokens = sentence_words[sent_idx]
            annotations = ['O'] * len(tokens)
            for (word_idx, label) in labels:
                if label == 'UserIDWindows':
                    label = 'UserIDGeneric'
                elif label == 'LastName':
                    label = 'FullName'
                if isinstance(word_idx, tuple):
                    start, end = word_idx
                    for i in range(start, end):
                        if i == start:
                            annotations[i] = 'B-' + label
                        else:
                            annotations[i] = 'I-' + label
                else:
                    # print(sentence_words[sent_idx][word_idx], label)
                    annotations[word_idx] = 'I-' + label
            outputs.append({'tokens': tokens, 'labels': annotations})

        return outputs

    def get_class_counts(self):
        classes = { tag for label in self.labels for tag in label }
        counts = ( Counter(label_list) for label_list in self.labels )
        class_counts = defaultdict(int)
        for cc in counts:
            for tag in cc:
                class_counts[tag] += cc[tag]
        return class_counts


    def print_class_counts(self):
        class_counts = self.get_class_counts()
        print('Sample Counts')
        for tag in class_counts:
            print(tag, ':', class_counts[tag])
