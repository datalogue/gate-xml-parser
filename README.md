# Gate XML Parser
XML Parser for converting from GATE's char-indexed annotations to sentence-word-indexed annotations using BIO tagging scheme.  Used for various ML tasks. 

# Example Usage
## Load Parser
` from gateparser.parser import GateBIOParser`

## Specify XML File, Encoding, and Structure
```python
parsed_xml = GateBIOParser('example-data/example-gate-export.xml', encoding='windows-1252', 
                                                        annotation_spec='GateDocument.AnnotationSet',
                                                        node_spec='GateDocument.TextWithNodes',
                                                        text_spec='GateDocument.TextWithNodes')
BIO = parsed_xml.BIO
```
BIO is a list of dictionaries representing sentences in the input, broken into matching tokens and labels
i.e. BIO[0] returns the following
```python
{'labels': ['O',  'O',         'O',         'B-FullName',  'I-FullName',  'O',  'I-UserIDWindows',  'O',  'O',    'O'],
 'tokens': ['*',  '11.11.2011','01:54:01',  'Kimb',         'Helper',     '(',  'HELPER',           ')',  'Tel',  '.']}
``` 
### Sanity Checking Class Counts
```python 
parsed_xml.print_class_counts()
```

#### Returns
```python
Sample Counts
O : 97
B-FullName : 2
I-FullName : 2
I-UserIDWindows : 2
B-TelNumber : 1
I-TelNumber : 2
```
