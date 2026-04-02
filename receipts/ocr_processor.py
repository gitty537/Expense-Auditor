import pytesseract
import cv2
import numpy as np
import re
from datetime import datetime
from PIL import Image
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

class ReceiptOCRProcessor:
    
    @staticmethod
    def configure():
        """Set Tesseract path if needed"""
        import platform
        if platform.system() == 'Windows':
            pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    
    @staticmethod
    def preprocess_image(image_path):
        """Enhance image for better OCR"""
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(denoised)
        _, binary = cv2.threshold(enhanced, 150, 255, cv2.THRESH_BINARY)
        return binary
    
    @staticmethod
    def extract_text(image_path, preprocess=True):
        """Extract text with optional preprocessing"""
        if preprocess:
            processed = ReceiptOCRProcessor.preprocess_image(image_path)
            text = pytesseract.image_to_string(processed, config='--oem 1 --psm 6')
        else:
            text = pytesseract.image_to_string(image_path, config='--oem 1 --psm 6')
        return text
    
    @staticmethod
    def extract_structured_data(image_path):
        """Extract with confidence scores and positions"""
        if image_path.lower().endswith('.pdf'):
            import fitz
            doc = fitz.open(image_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = Image.open(image_path)
            
        data = pytesseract.image_to_data(img, output_type='dict')
        
        words = []
        confidences = []
        
        for i in range(len(data['text'])):
            if int(data['conf'][i]) > 0:
                word = {
                    'text': data['text'][i],
                    'confidence': int(data['conf'][i]),
                    'x': int(data['left'][i]),
                    'y': int(data['top'][i]),
                    'width': int(data['width'][i]),
                    'height': int(data['height'][i])
                }
                words.append(word)
                confidences.append(int(data['conf'][i]))
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            'words': words,
            'average_confidence': avg_confidence,
            'raw_text': pytesseract.image_to_string(img)
        }
    
    @staticmethod
    def parse_receipt_fields(raw_text):
        """Extract merchant, date, amount from OCR text"""
        
        # Merchant (top line, usually all caps)
        merchant_match = re.search(r'^([A-Z\s&\-.,]+?)(?:\n|$)', raw_text, re.MULTILINE)
        merchant = merchant_match.group(1).strip() if merchant_match else 'Unknown'
        merchant = ' '.join(merchant.split())  # Clean whitespace
        
        # Date
        date_pattern = r'(?:DATE|TIME)?[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'
        date_match = re.search(date_pattern, raw_text, re.IGNORECASE)
        transaction_date = None
        if date_match:
            date_str = date_match.group(1)
            for fmt in ['%m/%d/%Y', '%d/%m/%Y', '%m-%d-%Y', '%d-%m-%Y']:
                try:
                    transaction_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        
        # Amount (after TOTAL keyword or largest currency value)
        amount_pattern = r'(?:TOTAL|SUBTOTAL|AMOUNT)[\s:]*\$?([\d,\.]+)'
        amount_match = re.search(amount_pattern, raw_text, re.IGNORECASE)
        total_amount = None
        
        if amount_match:
            amount_str = amount_match.group(1).replace(',', '')
            try:
                total_amount = float(amount_str)
            except ValueError:
                pass
        else:
            # Fallback: find last currency amount
            amounts = re.findall(r'\$?([\d]{1,5}[.,]\d{2})', raw_text)
            if amounts:
                try:
                    total_amount = float(amounts[-1].replace(',', ''))
                except ValueError:
                    pass
        
        # Currency
        currency_map = {
            '$': 'USD', 'USD': 'USD',
            '£': 'GBP', 'GBP': 'GBP',
            '¥': 'JPY', 'JPY': 'JPY',
            '€': 'EUR', 'EUR': 'EUR',
            'S$': 'SGD', 'SGD': 'SGD',
        }
        currency_code = 'USD'
        for symbol, code in currency_map.items():
            if symbol in raw_text:
                currency_code = code
                break

        return {
            'merchant_name': merchant,
            'transaction_date': transaction_date,
            'total_amount': total_amount,
            'currency_code': currency_code,
            'raw_text': raw_text
        }
    
    @staticmethod
    def assess_quality(image_path):
        """Score image quality and provide feedback"""
        if image_path.lower().endswith('.pdf'):
            import fitz
            doc = fitz.open(image_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=300)
            img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            img = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        else:
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        
        # Blur detection
        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        blur_score = min(laplacian_var / 500, 1.0)
        
        # Brightness
        brightness = cv2.mean(img)[0]
        brightness_score = 1.0 if 50 < brightness < 200 else 0.5
        
        # Overall
        overall_score = (blur_score * 0.7) + (brightness_score * 0.3)
        
        issues = []
        if laplacian_var < 100:
            issues.append("Image is blurry")
        if brightness < 50:
            issues.append("Image is too dark")
        if brightness > 200:
            issues.append("Image is too bright")
        
        return {
            'overall_score': overall_score,
            'is_acceptable': overall_score > 0.5,
            'issues': issues,
            'laplacian_variance': laplacian_var
        }

# Configure on module load
ReceiptOCRProcessor.configure()