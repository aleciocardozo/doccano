from .catalog import (
    CSV,
    JSON,
    JSONL,
    JSONF,
    AudioFile,
    CoNLL,
    Excel,
    FastText,
    Format,
    ImageFile,
    TextFile,
    TextLine,
)
from .parsers import (
    CoNLLParser,
    CSVParser,
    ExcelParser,
    FastTextParser,
    JSONFParser,
    JSONLParser,
    JSONParser,
    LineParser,
    PlainParser,
    TextFileParser,
)


def create_parser(file_format: Format, **kwargs):
    mapping = {
        TextFile.name: TextFileParser,
        TextLine.name: LineParser,
        CSV.name: CSVParser,
        JSONF.name: JSONFParser,
        JSONL.name: JSONLParser,
        JSON.name: JSONParser,
        FastText.name: FastTextParser,
        Excel.name: ExcelParser,
        CoNLL.name: CoNLLParser,
        ImageFile.name: PlainParser,
        AudioFile.name: PlainParser,
    }
    return mapping[file_format.name](**kwargs)
