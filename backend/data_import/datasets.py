import abc
import pandas as pd
from typing import List, Type

from django.contrib.auth.models import User

from .models import DummyLabelType
from .pipeline.catalog import RELATION_EXTRACTION, Format
from .pipeline.data import BaseData, BinaryData, TextData
from .pipeline.examples import Examples
from .pipeline.exceptions import FileParseException
from .pipeline.factories import create_parser
from .pipeline.label import CategoryLabel, Label, RelationLabel, SpanLabel, TextLabel
from .pipeline.label_types import LabelTypes
from .pipeline.labels import Categories, Labels, Relations, Spans, Texts
from .pipeline.makers import BinaryExampleMaker, ExampleMaker, LabelMaker
from .pipeline.readers import (
    DEFAULT_LABEL_COLUMN,
    DEFAULT_TEXT_COLUMN,
    FileName,
    Reader,
)
from label_types.models import CategoryType, LabelType, RelationType, SpanType
from projects.models import Project, ProjectType
from examples.models import Example
from labels.models import Span, Relation
from projects.models import AspectBasedSentimentAnalysisProject
from data_import.pipeline.makers import LabelMaker
from data_import.pipeline.makers import ExampleMaker
from data_import.pipeline.label_types import LabelTypes


class Dataset(abc.ABC):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        self.reader = reader
        self.project = project
        self.kwargs = kwargs

    def save(self, user: User, batch_size: int = 1000):
        raise NotImplementedError()

    @property
    def errors(self) -> List[FileParseException]:
        raise NotImplementedError()


class PlainDataset(Dataset):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.example_maker = ExampleMaker(project=project, data_class=TextData)

    def save(self, user: User, batch_size: int = 1000):
        for records in self.reader.batch(batch_size):
            examples = Examples(self.example_maker.make(records))
            examples.save()

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors


class DatasetWithSingleLabelType(Dataset):
    data_class: Type[BaseData]
    label_class: Type[Label]
    label_type = LabelType
    labels_class = Labels

    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.types = LabelTypes(self.label_type)
        self.example_maker = ExampleMaker(
            project=project,
            data_class=self.data_class,
            column_data=kwargs.get("column_data") or DEFAULT_TEXT_COLUMN,
            exclude_columns=[kwargs.get("column_label") or DEFAULT_LABEL_COLUMN],
        )
        self.label_maker = LabelMaker(
            column=kwargs.get("column_label") or DEFAULT_LABEL_COLUMN, label_class=self.label_class
        )

    def save(self, user: User, batch_size: int = 1000):
        for records in self.reader.batch(batch_size):
            # create examples
            examples = Examples(self.example_maker.make(records))
            examples.save()

            # create label types
            labels = self.labels_class(self.label_maker.make(records), self.types)
            labels.clean(self.project)
            labels.save_types(self.project)

            # create Labels
            labels.save(user, examples)

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors + self.label_maker.errors


class BinaryDataset(Dataset):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.example_maker = BinaryExampleMaker(project=project, data_class=BinaryData)

    def save(self, user: User, batch_size: int = 1000):
        for records in self.reader.batch(batch_size):
            examples = Examples(self.example_maker.make(records))
            examples.save()

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors


class TextClassificationDataset(DatasetWithSingleLabelType):
    data_class = TextData
    label_class = CategoryLabel
    label_type = CategoryType
    labels_class = Categories


class SequenceLabelingDataset(DatasetWithSingleLabelType):
    data_class = TextData
    label_class = SpanLabel
    label_type = SpanType
    labels_class = Spans


class Seq2seqDataset(DatasetWithSingleLabelType):
    data_class = TextData
    label_class = TextLabel
    label_type = DummyLabelType
    labels_class = Texts


class RelationExtractionDataset(Dataset):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.span_types = LabelTypes(SpanType)
        self.relation_types = LabelTypes(RelationType)
        self.example_maker = ExampleMaker(
            project=project,
            data_class=TextData,
            column_data=kwargs.get("column_data") or DEFAULT_TEXT_COLUMN,
            exclude_columns=["entities", "relations"],
        )
        self.span_maker = LabelMaker(column="entities", label_class=SpanLabel)
        self.relation_maker = LabelMaker(column="relations", label_class=RelationLabel)

    def save(self, user: User, batch_size: int = 1000):
        for records in self.reader.batch(batch_size):
            # create examples
            examples = Examples(self.example_maker.make(records))
            examples.save()

            # create label types
            spans = Spans(self.span_maker.make(records), self.span_types)
            spans.clean(self.project)
            spans.save_types(self.project)

            relations = Relations(self.relation_maker.make(records), self.relation_types)
            relations.clean(self.project)
            relations.save_types(self.project)

            # create Labels
            spans.save(user, examples)
            relations.save(user, examples, spans=spans)

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors + self.span_maker.errors + self.relation_maker.errors


class CategoryAndSpanDataset(Dataset):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.category_types = LabelTypes(CategoryType)
        self.span_types = LabelTypes(SpanType)
        self.example_maker = ExampleMaker(
            project=project,
            data_class=TextData,
            column_data=kwargs.get("column_data") or DEFAULT_TEXT_COLUMN,
            exclude_columns=["cats", "entities"],
        )
        self.category_maker = LabelMaker(column="cats", label_class=CategoryLabel)
        self.span_maker = LabelMaker(column="entities", label_class=SpanLabel)

    def save(self, user: User, batch_size: int = 1000):
        for records in self.reader.batch(batch_size):
            # create examples
            examples = Examples(self.example_maker.make(records))
            examples.save()

            # create label types
            categories = Categories(self.category_maker.make(records), self.category_types)
            categories.clean(self.project)
            categories.save_types(self.project)

            spans = Spans(self.span_maker.make(records), self.span_types)
            spans.clean(self.project)
            spans.save_types(self.project)

            # create Labels
            categories.save(user, examples)
            spans.save(user, examples)

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors + self.category_maker.errors + self.span_maker.errors


class AspectBasedSentimentAnalysisDataset(Dataset):
    def __init__(self, reader: Reader, project: Project, **kwargs):
        super().__init__(reader, project, **kwargs)
        self.category_types = LabelTypes(CategoryType)
        self.span_types = LabelTypes(SpanType)
        self.relation_types = LabelTypes(RelationType)
        self.example_maker = ExampleMaker(
            project=project,
            data_class=TextData,
            column_data=kwargs.get("column_data") or "text",
            exclude_columns=["entities", "relations", "cats", "aspect", "category", "opinion", "polarity", 
                            "aspect_start", "aspect_end", "opinion_start", "opinion_end"],
        )
        self.category_maker = LabelMaker(column="cats", label_class=CategoryLabel)
        self.span_maker = LabelMaker(column="entities", label_class=SpanLabel)
        self.relation_maker = LabelMaker(column="relations", label_class=RelationLabel)
        
        self.column_data = kwargs.get("column_data") or "text"
        self.column_category = kwargs.get("column_category") or "category"
        self.column_aspect = kwargs.get("column_aspect") or "aspect"
        self.column_opinion = kwargs.get("column_opinion") or "opinion"
        self.column_polarity = kwargs.get("column_polarity") or "polarity"
        self.column_aspect_start = kwargs.get("column_aspect_start") or "aspect_start"
        self.column_aspect_end = kwargs.get("column_aspect_end") or "aspect_end"
        self.column_opinion_start = kwargs.get("column_opinion_start") or "opinion_start"
        self.column_opinion_end = kwargs.get("column_opinion_end") or "opinion_end"

    def ensure_label_colors(self):
        for cat_type in CategoryType.objects.filter(project=self.project):
            cat_type.background_color = "#0d7781"
            cat_type.text_color = "#ffffff"
            cat_type.save()

        aspect_type, created = SpanType.objects.get_or_create(
            project=self.project,
            text="aspect",
            defaults={
                "background_color": "#11a4ed",
                "text_color": "#ffffff",
                "suffix_key": "",
            }
        )
        if not created:
            aspect_type.background_color = "#11a4ed"
            aspect_type.text_color = "#ffffff"
            aspect_type.save()

        opinion_type, created = SpanType.objects.get_or_create(
            project=self.project,
            text="opinion",
            defaults={
                "background_color": "#c83936",
                "text_color": "#ffffff",
                "suffix_key": "",
            }
        )
        if not created:
            opinion_type.background_color = "#c83936"
            opinion_type.text_color = "#ffffff"
            opinion_type.save()
        
    def save(self, user: User, batch_size: int = 1000):
        for df_records in self.reader.batch(batch_size):            
            examples_data = self.example_maker.make(df_records)
            examples = Examples(examples_data)
            examples.save()
            
            example_uuids = [str(example.uuid) for example in examples_data]
            
            required_aspect_columns = {self.column_data, self.column_aspect, self.column_aspect_start, self.column_aspect_end}
            df_columns_set = set(df_records.columns)
            
            if required_aspect_columns.issubset(df_columns_set):
                df_transformed = df_records.copy()
                
                # aspect and opinion
                entities_list = []
                for index, row in df_transformed.iterrows():
                    example_entities = []
                    
                    aspect = row.get(self.column_aspect)
                    aspect_start = row.get(self.column_aspect_start)
                    aspect_end = row.get(self.column_aspect_end)
                    if (aspect is not None and aspect_start is not None and aspect_end is not None):
                        try:
                            aspect_start = int(aspect_start)
                            aspect_end = int(aspect_end)
                            if 0 <= aspect_start < aspect_end:
                                example_entities.append({"label": "aspect", "start_offset": aspect_start, "end_offset": aspect_end})
                        except (ValueError, TypeError):
                            pass
                    
                    if {self.column_opinion, self.column_opinion_start, self.column_opinion_end}.issubset(df_columns_set):
                        opinion = row.get(self.column_opinion)
                        opinion_start = row.get(self.column_opinion_start)
                        opinion_end = row.get(self.column_opinion_end)
                        if (opinion is not None and opinion_start is not None and opinion_end is not None):
                            try:
                                opinion_start = int(opinion_start)
                                opinion_end = int(opinion_end)
                                if 0 <= opinion_start < opinion_end:
                                    example_entities.append({"label": "opinion", "start_offset": opinion_start, "end_offset": opinion_end})
                            except (ValueError, TypeError):
                                pass
                    
                    entities_list.append(example_entities)
                
                df_transformed['entities'] = entities_list
                
                spans = Spans(self.span_maker.make(df_transformed), self.span_types)
                spans.clean(self.project)
                spans.save_types(self.project)
                spans.save(user, examples)
                
                
                # category
                if hasattr(self.project, 'is_quadruple_extraction') and self.project.is_quadruple_extraction:
                    categories_data = []
                    for index, row in df_transformed.iterrows():
                        category = row.get(self.column_category)
                        
                        if category:
                            example_uuid = example_uuids[index]
                            categories_data.append({
                                'example_uuid': example_uuid,
                                'cats': category
                            })
                    
                    if categories_data:
                        df_categories = pd.DataFrame(categories_data)
                        
                        categories = Categories(self.category_maker.make(df_categories), self.category_types)
                        categories.clean(self.project)
                        categories.save_types(self.project)
                        categories.save(user, examples)
                
                
                self.ensure_label_colors()
                
                
                example_uuids_set = set(example_uuids)
                db_examples = Example.objects.filter(uuid__in=example_uuids_set)
                
                uuid_to_example = {}
                for example in db_examples:
                    uuid_to_example[str(example.uuid)] = example
                
                example_ids = [example.id for example in db_examples]
                db_spans = Span.objects.filter(example_id__in=example_ids)
                
                id_to_span = {}
                for span in db_spans:
                    example_uuid = str(span.example.uuid)
                    id_to_span[(span.id, example_uuid)] = span
                
                example_uuid_to_spans = {}
                for span in db_spans:
                    example_uuid = str(span.example.uuid)
                    if example_uuid not in example_uuid_to_spans:
                        example_uuid_to_spans[example_uuid] = []
                    example_uuid_to_spans[example_uuid].append(span)
                

                # relation
                relations_list = []
                for index, row in df_transformed.iterrows():
                    example_relations = []
                    polarity = row.get(self.column_polarity)
                    example_uuid = example_uuids[index]
                    
                    if (self.project.use_relation and polarity is not None and 
                        {self.column_opinion, self.column_opinion_start, self.column_opinion_end}.issubset(df_columns_set) and 
                        len(entities_list[index]) == 2 and 
                        example_uuid in example_uuid_to_spans and 
                        len(example_uuid_to_spans[example_uuid]) >= 2):
                        
                        example_spans = example_uuid_to_spans[example_uuid]
                        
                        aspect_span = None
                        opinion_span = None
                        for span in example_spans:
                            if span.label.text == "aspect":
                                aspect_span = span
                            elif span.label.text == "opinion":
                                opinion_span = span
                        
                        if aspect_span and opinion_span:
                            example_relations.append({
                                "from_id": aspect_span.id, 
                                "to_id": opinion_span.id, 
                                "type": polarity
                            })
                    
                    relations_list.append(example_relations)
                 
                df_transformed['relations'] = relations_list
                relations = Relations(self.relation_maker.make(df_transformed), self.relation_types)
                relations.clean(self.project)
                relations.save_types(self.project)
                
                class SpansWrapper:
                    def __init__(self, spans, id_to_span):
                        self.spans = spans
                        self.id_to_span = id_to_span
                
                spans_wrapper = SpansWrapper(spans, id_to_span)
                
                relations.save(user, examples, spans=spans_wrapper)

    @property
    def errors(self) -> List[FileParseException]:
        return self.reader.errors + self.example_maker.errors + self.category_maker.errors + self.span_maker.errors + self.relation_maker.errors


def select_dataset(project: Project, task: str, file_format: Format) -> Type[Dataset]:
    mapping = {
        ProjectType.DOCUMENT_CLASSIFICATION: TextClassificationDataset,
        ProjectType.SEQUENCE_LABELING: SequenceLabelingDataset,
        RELATION_EXTRACTION: RelationExtractionDataset,
        ProjectType.SEQ2SEQ: Seq2seqDataset,
        ProjectType.INTENT_DETECTION_AND_SLOT_FILLING: CategoryAndSpanDataset,
        ProjectType.IMAGE_CLASSIFICATION: BinaryDataset,
        ProjectType.IMAGE_CAPTIONING: BinaryDataset,
        ProjectType.BOUNDING_BOX: BinaryDataset,
        ProjectType.SEGMENTATION: BinaryDataset,
        ProjectType.SPEECH2TEXT: BinaryDataset,
        ProjectType.DOCUMENT_SENTIMENT_ANALYSIS: TextClassificationDataset,
        ProjectType.ASPECT_BASED_SENTIMENT_ANALYSIS: AspectBasedSentimentAnalysisDataset,
    }
    if task not in mapping:
        task = project.project_type
    if project.is_text_project and file_format.is_plain_text():
        return PlainDataset
    return mapping[task]


def load_dataset(task: str, file_format: Format, data_files: List[FileName], project: Project, **kwargs) -> Dataset:
    parser = create_parser(file_format, **kwargs)
    reader = Reader(data_files, parser)
    dataset_class = select_dataset(project, task, file_format)
    return dataset_class(reader, project, **kwargs)
