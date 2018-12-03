# Gate XML Parser
XML Parser for converting from GATE's char-indexed annotations to sentence-word-indexed annotations using BIO tagging scheme.  Used for various ML tasks. 

# Example Usage
## Load Parser
```python
from gateparser.parser import GateBIOParser
```

## Specify XML File, Encoding, and Structure
```python
parsed_xml = GateBIOParser('example-data/example-gate-export.xml', encoding='windows-1252', 
                                                        annotation_spec='GateDocument.AnnotationSet',
                                                        node_spec='GateDocument.TextWithNodes',
                                                        text_spec='GateDocument.TextWithNodes')
BIO = parsed_xml.BIO
```
BIO is a dictionary matching input tokens to their labels

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
