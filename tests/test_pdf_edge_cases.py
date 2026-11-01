import io
import shutil
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError

from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject

from mailnotes.documents import pdf_text
from test_documents_ai import sample_pdf


def document(*pages):
    writer=PdfWriter()
    for text in pages:
        if text:
            writer.append_pages_from_reader(PdfReader(io.BytesIO(sample_pdf(text))))
        else:
            writer.add_blank_page(width=600,height=800)
    output=io.BytesIO();writer.write(output)
    return output.getvalue()


def render_page(command, **kwargs):
    Path(command[-1]+'-1.png').write_bytes(b'image-test')


def ocr(content, finish='stop'):
    return {'choices':[{'finish_reason':finish,'message':{'content':content}}]}


class PDFEdgeCasesTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('pdftoppm'), 'Poppler integration requires pdftoppm')
    def test_actual_poppler_page_render_uses_the_expected_image_file(self):
        with patch('mailnotes.core.request_json',return_value=ocr('Actual image conversion reached the mocked OCR endpoint.')) as request:
            text,warning=pdf_text(document('Keep original text.',None),ocr=True,api_key='test-key',endpoint='https://provider.example')
        self.assertEqual(request.call_count,1)
        self.assertIn('Actual image conversion',text)
        self.assertIn('Keep original text.',text)
        self.assertNotIn('thất bại',warning)

    def test_mixed_pdf_ocr_only_reads_missing_page_and_keeps_document_order(self):
        raw=document('First page has selectable text.',None,'Last page has selectable text.')
        with patch('mailnotes.documents.subprocess.run',side_effect=render_page) as render,patch('mailnotes.core.request_json',return_value=ocr('Scanned middle page, deadline 30 November.')) as request:
            text,warning=pdf_text(raw,ocr=True,api_key='test-key',endpoint='https://provider.example')
        self.assertEqual(request.call_count,1)
        command=render.call_args.args[0]
        self.assertEqual(command[command.index('-f')+1],'2')
        self.assertEqual(command[command.index('-l')+1],'2')
        self.assertLess(text.index('First'),text.index('Scanned'))
        self.assertLess(text.index('Scanned'),text.index('Last'))
        self.assertNotIn('chưa được đọc',warning)

    def test_partial_ocr_failure_preserves_successful_pages(self):
        with patch('mailnotes.documents.subprocess.run',side_effect=render_page),patch('mailnotes.core.request_json',side_effect=[ocr('Content successfully read from the first scanned page.'),URLError('offline')]):
            text,warning=pdf_text(document(None,None),ocr=True,api_key='test-key',endpoint='https://provider.example')
        self.assertIn('successfully read',text)
        self.assertIn('thất bại hoặc quá thời gian ở trang 2',warning)
        self.assertIn('1 trang không có lớp chữ',warning)

    def test_short_ocr_is_preserved_and_truncated_ocr_is_explicit(self):
        with patch('mailnotes.documents.subprocess.run',side_effect=render_page),patch('mailnotes.core.request_json',return_value=ocr('Số 01/2026','length')) as request:
            text,warning=pdf_text(document(None),ocr=True,api_key='test-key',endpoint='https://provider.example')
        self.assertEqual(text,'Số 01/2026')
        self.assertIn('giới hạn đầu ra ở trang 1',warning)
        self.assertLessEqual(request.call_args.kwargs['timeout'],60)

    def test_page_extraction_error_does_not_discard_other_pages(self):
        original=PageObject.extract_text
        def extract(page,*args,**kwargs):
            if '/Contents' not in page:raise ValueError('Broken text stream')
            return original(page,*args,**kwargs)
        with patch.object(PageObject,'extract_text',extract):
            text,warning=pdf_text(document('Keep the readable page.',None))
        self.assertIn('Keep the readable page.',text)
        self.assertIn('không đọc được ở trang 2',warning)
