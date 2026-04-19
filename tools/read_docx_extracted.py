import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            
            tree = ET.XML(xml_content)
            
            # namespaces
            WORD_NAMESPACE = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
            PARA = WORD_NAMESPACE + 'p'
            TEXT = WORD_NAMESPACE + 't'
            
            paragraphs = []
            for paragraph in tree.iter(PARA):
                texts = [node.text for node in paragraph.iter(TEXT) if node.text]
                if texts:
                    paragraphs.append(''.join(texts))
            
            print(f"Total entries: {len(paragraphs)}")
            for p in paragraphs[:30]:
                print(p)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    path = r"C:\Users\21543\Desktop\ai-lab-management-main\1.20220517124-谢北宸-基于AI的高校实验室智能管理系统设计与实现.docx"
    read_docx(path)
