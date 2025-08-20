import requests
import json
import time
import os
import re

class ContentUnderstandingClient:
    def __init__(self, endpoint, api_key):
        self.endpoint = endpoint.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'Ocp-Apim-Subscription-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def analyze_image_for_people(self, file_url):
        """
        Analyze an image and count people using smart text parsing
        
        Args:
            file_url (str): Public URL to the image
            
        Returns:
            dict: Analysis results with people count
        """
        
        # Analyze with image analyzer first
        results = self.analyze_document(file_url, "prebuilt-imageAnalyzer")
        people_count = 0
        
        if 'result' in results and 'contents' in results['result']:
            content = results['result']['contents'][0]
            
            # Extract description text
            description = ""
            if 'fields' in content and 'Summary' in content['fields']:
                description = content['fields']['Summary'].get('valueString', '')
            elif 'markdown' in content:
                description = content['markdown']
            
            # Smart people counting from description
            people_count = self._extract_people_count(description)
            
            print(f"📄 Image Description: {description}")
            
        return {
            'people_counts': people_count,
            'description': description,
            'full_results': results
        }
    
    def _extract_people_count(self, text):
        """Extract people count from text description"""
        text_lower = text.lower()
        
        # Number word to digit mapping
        number_words = {
            'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
            'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20
        }
        
        # Patterns to look for
        patterns = [
            r'(?:group of|crowd of)?\s*(\w+)\s+(?:people|persons|individuals|men|women|adults|children)',
            r'(\w+)\s+(?:people|persons|individuals|men|women|adults|children)',
            r'(\d+)\s+(?:people|persons|individuals|men|women|adults|children)',
            r'(?:shows|depicts|contains|has|features)\s+(\w+)\s+(?:people|persons)',
            r'(\w+)\s+(?:people|persons)\s+(?:sitting|standing|walking|gathered)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Try to convert to number
                if match.isdigit():
                    return int(match)
                elif match in number_words:
                    return number_words[match]
        
        # Look for specific phrases
        if 'couple' in text_lower:
            return 2
        elif 'trio' in text_lower or 'three people' in text_lower:
            return 3
        elif 'quartet' in text_lower or 'four people' in text_lower:
            return 4
        elif 'crowd' in text_lower or 'many people' in text_lower:
            return 10  # Estimate for crowd
        elif 'few people' in text_lower:
            return 3  # Estimate for "few"
        elif 'several people' in text_lower:
            return 5  # Estimate for "several"
        
        return 0
    
    def analyze_document(self, file_url, analyzer_id="prebuilt-documentAnalyzer"):
        """Generic analysis method"""
        analyze_url = f"{self.endpoint}/contentunderstanding/analyzers/{analyzer_id}:analyze"
        params = {"api-version": "2025-05-01-preview"}
        payload = {"url": file_url}
        
        print(f"🚀 Starting analysis for: {file_url}")
        
        response = requests.post(analyze_url, headers=self.headers, params=params, json=payload)
        
        if response.status_code != 202:
            raise Exception(f"Failed to start analysis: {response.status_code} - {response.text}")
        
        operation_location = response.headers.get('Operation-Location')
        request_id = response.headers.get('request-id')
        
        print(f"✅ Analysis started. Request ID: {request_id}")
        
        return self._poll_for_results(operation_location)
    
    def _poll_for_results(self, operation_location, max_wait_time=60):
        """Poll for results"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            print("⏳ Checking analysis status...")
            
            response = requests.get(operation_location, headers=self.headers)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get results: {response.status_code} - {response.text}")
            
            result = response.json()
            status = result.get('status')
            
            if status == 'Succeeded':
                print("🎉 Analysis completed!")
                return result
            elif status == 'Failed':
                raise Exception(f"Analysis failed: {result}")
            elif status in ['Running', 'NotStarted']:
                print(f"📊 Status: {status}")
                time.sleep(2)
            else:
                raise Exception(f"Unknown status: {status}")
        
        raise Exception("Analysis timed out")

def main():
    # Your Azure AI Content Understanding service details
    ENDPOINT = "https://content-understanding-smywgt2vzzxmi.cognitiveservices.azure.com/"
    API_KEY = os.getenv('CONTENT_UNDERSTANDING_KEY')
    
    if not API_KEY:
        print("❌ Please set the CONTENT_UNDERSTANDING_KEY environment variable")
        print("💡 Get your key with: az cognitiveservices account keys list --name content-understanding-smywgt2vzzxmi --resource-group rg-document-intelligence --query key1 --output tsv")
        return
    
    client = ContentUnderstandingClient(ENDPOINT, API_KEY)
    
    # Test images with different numbers of people
    test_images = [
        {
            "url": "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=800",
            "description": "Group of friends"
        },
        {
            "url": "https://images.unsplash.com/photo-1511632765486-a01980e01a18?w=800", 
            "description": "Business team"
        },
        {
            "url": "https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800",
            "description": "Team meeting"
        }
    ]
    
    for i, image in enumerate(test_images, 1):
        print(f"\n🖼️ Test {i}: {image['description']}")
        print("=" * 60)
        
        try:
            results = client.analyze_image_for_people(image['url'])
            print(f"\n👥 PEOPLE COUNT: {results['people_count']}")
            
            # Save results
            filename = f'people_count_test_{i}.json'
            with open(filename, 'w') as f:
                json.dump(results['full_results'], f, indent=2)
            print(f"💾 Results saved to {filename}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print("\n" + "="*60)

def test_single_image(image_url):
    """Test a single image URL"""
    # Your Azure AI Content Understanding service details
    ENDPOINT = "https://content-understanding-smywgt2vzzxmi.cognitiveservices.azure.com/"
    API_KEY = os.getenv('CONTENT_UNDERSTANDING_KEY')
    
    if not API_KEY:
        print("❌ Please set the CONTENT_UNDERSTANDING_KEY environment variable")
        print("💡 Get your key with: az cognitiveservices account keys list --name content-understanding-smywgt2vzzxmi --resource-group rg-document-intelligence --query key1 --output tsv")
        return
    
    client = ContentUnderstandingClient(ENDPOINT, API_KEY)
    
    try:
        results = client.analyze_image_for_people(image_url)
        print(f"\n👥 PEOPLE COUNT: {results['people_count']}")
        return results['people_count']
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test with provided URL
        image_url = sys.argv[1]
        test_single_image(image_url)
    else:
        # Run all tests
        main()
