# item_categorizer.py
import logging
import re
import numpy as np
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class HybridCategorizer:
    """
    A powerful free categorizer that combines multiple techniques,
    with lazy initialization to avoid accessing database during app startup.
    """
    
    def __init__(self):
        self.categories = {}
        self.default_category_id = None
        self.initialized = False
        self.tfidf = None
        self.category_vectors = {}
        self.category_keywords = {}
        self.category_descriptions = {}
        
    def initialize(self):
        """
        Load category data and initialize the categorizer.
        Only called when needed, not during app startup.
        """
        if self.initialized:
            return True
            
        try:
            from .models import Category
            
            # Get categories from database
            categories = Category.objects.all()
            
            if not categories.exists():
                logger.warning("No categories found in database")
                return False
            
            # Store category information
            for category in categories:
                self.categories[category.id] = category.name
                
                # Set default category (Others)
                if "other" in category.name.lower():
                    self.default_category_id = category.id
            
            # If no "Others" category found, use the last category
            if self.default_category_id is None and categories.exists():
                self.default_category_id = categories.last().id
                
            # Create category-specific keywords and descriptions
            self._setup_category_data()
            
            # Initialize the TF-IDF vectorizer
            self._initialize_tfidf()
            
            self.initialized = True
            logger.info("Categorizer initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing categorizer: {str(e)}")
            return False
    
    def _setup_category_data(self):
        """
        Create detailed keywords and descriptions for each category
        """
        # Define rich descriptions and keywords for each category
        category_data = {
            "Electronics & Gadgets": {
                "keywords": ["laptop", "phone", "smartphone", "headphone", "earphone", "tablet", 
                             "charger", "adapter", "speaker", "mouse", "keyboard", "monitor", 
                             "camera", "gadget", "cable", "electronic", "tech", "computer", "pc",
                             "device", "calculator", "watch", "smart", "digital", "gaming",
                             "console", "playstation", "xbox", "nintendo", "power bank", "calculator", "electric", "kettle", "VR"],
                "description": "Electronic devices and gadgets including laptops, phones, headphones, tablets, and tech accessories"
            },
            "Kitchen & Cooking": {
                "keywords": ["pot", "pan", "plate", "bowl", "knife", "fork", "spoon", "mug", "cup",
                             "microwave", "refrigerator", "fridge", "kettle", "blender", "mixer",
                             "toaster", "cooker", "utensil", "cookware", "kitchen", "cooking",
                             "spatula", "container", "storage", "coffee", "tea", "bottle", "jar",
                             "food", "appliance", "gas", "stove", "dish", "cutlery", "cup", "peanut", "butter"],
                "description": "Kitchen items and cooking supplies for preparing and storing food"
            },
            "Books & Study Materials": {
                "keywords": ["book", "textbook", "novel", "study", "note", "notebook", "pen", 
                             "pencil", "highlighter", "stationery", "paper", "binder", "folder",
                             "calculator", "academic", "course", "semester", "subject", "guide",
                             "manual", "reference", "dictionary", "journal", "magazine", "reading",
                             "literature", "fiction", "nonfiction", "educational", "learning", "chem", "bio", "dbms", "math", "phy", "history", "geography", "english", "language", "grammar", "vocabulary", "text", "study material"],
                "description": "Books, textbooks, and study materials for academic courses and reading"
            },
            "Sports & Fitness Gear": {
                "keywords": ["sport", "fitness", "exercise", "gym", "workout", "ball", "bat", 
                             "racket", "yoga", "mat", "weight", "dumbbell", "running", "shoe",
                             "bicycle", "bike", "cricket", "football", "soccer", "basketball",
                             "volleyball", "badminton", "tennis", "athletic", "train", "cardio",
                             "jersey", "shorts", "track", "equipment", "swimming", "sports"],
                "description": "Sports equipment and fitness gear for physical activities and exercise"
            },
            "Musical Instruments": {
                "keywords": ["guitar", "piano", "keyboard", "drum", "violin", "flute", "ukulele", 
                             "bass", "instrument", "musical", "music", "play", "song", "sound",
                             "audio", "amplifier", "speaker", "headphone", "microphone", "record",
                             "musician", "band", "orchestra", "string", "electric", "acoustic",
                             "capo", "tuner", "pick", "bow", "saxophone", "trumpet", "harmonica"],
                "description": "Musical instruments and related equipment for playing and learning music"
            },
            "Dorm & Bedroom Essentials": {
                "keywords": ["bed", "mattress", "pillow", "sheet", "blanket", "duvet", "comforter", 
                             "bedding", "curtain", "lamp", "desk", "chair", "mirror", "storage",
                             "box", "organizer", "hanger", "rack", "dorm", "room", "sleep", "night",
                             "alarm", "clock", "fan", "heater", "hostel", "dorm", "bedroom", "essential", "cooler", "tray", "bean bag", ],
                "description": "Essential items for dorm rooms and bedrooms such as bedding, storage, and comfort items"
            },
            "Room Decor": {
                "keywords": ["decor", "decoration", "poster", "frame", "light", "lamp", "plant", 
                             "flower", "wall", "art", "picture", "photo", "cushion", "pillow",
                             "rug", "carpet", "curtain", "blind", "fairy", "string", "led", "strip",
                             "ornament", "figurine", "statue", "candle", "vase", "decorative",
                             "aesthetic", "tapestry", "flag", "banner", "disco"],
                "description": "Decorative items to personalize and beautify living spaces"
            },
            "Community & Shared Resources": {
                "keywords": ["community", "shared", "common", "resource", "board", "game", "card", 
                             "puzzle", "dvd", "movie", "book", "magazine", "tool", "equipment",
                             "party", "event", "activity", "group", "social", "communal", "utility",
                             "public", "collective", "share", "borrow", "lend", "temporary", "club",
                             "society", "organization", "gathering"],
                "description": "Items intended for shared or communal use among multiple students"
            },
            "Digital Subscriptions & Accounts": {
                "keywords": ["subscription", "account", "digital", "online", "service", "streaming", 
                             "netflix", "amazon", "prime", "spotify", "apple", "music", "platform",
                             "membership", "premium", "access", "login", "credential", "password",
                             "wifi", "internet", "cloud", "storage", "software", "license", "code",
                             "key", "activation", "download", "virtual", "game", "gaming"],
                "description": "Digital accounts, subscription services, and online platform memberships"
            },
            "Others": {
                "keywords": [],
                "description": "Miscellaneous items that don't fit into other categories"
            }
        }
        
        # Map to each category in the database
        for cat_id, cat_name in self.categories.items():
            # Look for exact match in the predefined data
            if cat_name in category_data:
                self.category_keywords[cat_id] = category_data[cat_name]["keywords"]
                self.category_descriptions[cat_id] = category_data[cat_name]["description"]
                continue
                
            # If no exact match, look for best partial match
            best_match = None
            highest_similarity = 0
            
            for predefined_name, data in category_data.items():
                # Simple word overlap similarity
                words1 = set(cat_name.lower().split())
                words2 = set(predefined_name.lower().split())
                
                # Calculate Jaccard similarity
                if not words1 or not words2:
                    similarity = 0
                else:
                    similarity = len(words1.intersection(words2)) / len(words1.union(words2))
                
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = predefined_name
            
            # Use the best match if similarity is reasonable
            if best_match and highest_similarity > 0.2:
                self.category_keywords[cat_id] = category_data[best_match]["keywords"]
                self.category_descriptions[cat_id] = category_data[best_match]["description"]
            else:
                # Create generic keywords from the category name
                words = re.findall(r'\w+', cat_name.lower())
                self.category_keywords[cat_id] = words
                self.category_descriptions[cat_id] = f"Items related to {cat_name}"
    
    def _initialize_tfidf(self):
        """Initialize TF-IDF vectorizer with category descriptions"""
        try:
            # Create corpus from category descriptions and keywords
            corpus = []
            category_ids = []
            
            for cat_id, keywords in self.category_keywords.items():
                # Add keywords multiple times to increase their weight
                text = " ".join(keywords) + " " + " ".join(keywords)
                if cat_id in self.category_descriptions:
                    text += " " + self.category_descriptions[cat_id]
                corpus.append(text)
                category_ids.append(cat_id)
            
            # Initialize and fit TF-IDF vectorizer
            self.tfidf = TfidfVectorizer(
                max_features=2000,
                stop_words='english',
                ngram_range=(1, 2)  # Use unigrams and bigrams
            )
            
            # Create TF-IDF vectors for each category
            vectors = self.tfidf.fit_transform(corpus)
            
            # Store category vectors
            for i, cat_id in enumerate(category_ids):
                self.category_vectors[cat_id] = vectors[i]
            
            return True
        except Exception as e:
            logger.error(f"Error initializing TF-IDF: {str(e)}")
            return False
    
    def _compute_keyword_score(self, text, cat_id):
        """Compute keyword matching score for a text and category"""
        score = 0
        text = text.lower()
        
        # Get keywords for this category
        keywords = self.category_keywords.get(cat_id, [])
        
        # Check for each keyword
        for keyword in keywords:
            # Full word match (higher score)
            pattern = r'\b' + re.escape(keyword) + r'\b'
            matches = re.findall(pattern, text)
            score += len(matches) * 2  # Higher weight for full matches
            
            # Partial matches
            if len(keyword) > 3 and keyword in text:
                score += 0.5
        
        return score
    
    def _compute_tfidf_similarity(self, text):
        """Compute TF-IDF similarity between text and each category"""
        try:
            # Transform text using fitted vectorizer
            text_vector = self.tfidf.transform([text])
            
            # Calculate similarity to each category
            similarities = {}
            for cat_id, cat_vector in self.category_vectors.items():
                similarity = cosine_similarity(text_vector, cat_vector)[0][0]
                similarities[cat_id] = similarity
                
            return similarities
        except Exception as e:
            logger.error(f"Error computing TF-IDF similarity: {str(e)}")
            return {}
    
    def categorize(self, name, description=""):
        """
        Categorize an item using multiple techniques
        """
        # Initialize if not already done - lazy loading
        if not self.initialized:
            success = self.initialize()
            if not success:
                # If initialization fails, try to find a default category directly
                try:
                    from .models import Category
                    default_cat = Category.objects.filter(name__icontains="other").first()
                    if default_cat:
                        return default_cat.id
                    else:
                        default_cat = Category.objects.first()
                        if default_cat:
                            return default_cat.id
                except Exception:
                    # Can't do anything here
                    return None
        
        # Combine name and description, with more weight on name
        text = name
        if description:
            text = f"{name} {name} {description}"  # Repeat name to give it more weight
        
        try:
            # Method 1: TF-IDF similarity
            tfidf_scores = self._compute_tfidf_similarity(text)
            
            # Method 2: Keyword matching
            keyword_scores = {}
            for cat_id in self.categories.keys():
                keyword_scores[cat_id] = self._compute_keyword_score(text, cat_id)
            
            # Combine scores with weights
            final_scores = {}
            for cat_id in self.categories.keys():
                # Weight TF-IDF more heavily as it's more sophisticated
                tfidf_weight = 0.7
                keyword_weight = 0.3
                
                tfidf_score = tfidf_scores.get(cat_id, 0)
                keyword_score = keyword_scores.get(cat_id, 0)
                
                # Normalize keyword scores (if any are non-zero)
                max_keyword = max(keyword_scores.values()) if keyword_scores and max(keyword_scores.values()) > 0 else 1
                norm_keyword_score = keyword_score / max_keyword if max_keyword > 0 else 0
                
                # Calculate weighted score
                final_scores[cat_id] = (tfidf_score * tfidf_weight) + (norm_keyword_score * keyword_weight)
            
            # Find category with highest score
            if final_scores:
                best_category_id = max(final_scores, key=final_scores.get)
                best_score = final_scores[best_category_id]
                
                # Log the result
                logger.info(f"Categorized '{name}' as '{self.categories[best_category_id]}' with score {best_score:.2f}")
                
                # Use default category if confidence is too low
                if best_score < 0.1:
                    logger.info(f"Low confidence score ({best_score:.2f}), using default category")
                    return self.default_category_id
                    
                return best_category_id
            
        except Exception as e:
            logger.error(f"Error during categorization: {str(e)}")
        
        # Fallback to default category
        return self.default_category_id

# Create a global instance
categorizer = HybridCategorizer()