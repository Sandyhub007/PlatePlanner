# 🛒 Phase 3: Shopping List Service - Requirements & Implementation Plan

**Project:** Plate Planner API  
**Phase:** 3 - Shopping List Generation & Management  
**Timeline:** 4 weeks  
**Status:** 📋 Planning  
**Owner:** Sandilya Chimalamarri

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [Technical Architecture](#technical-architecture)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)
7. [Implementation Plan](#implementation-plan)
8. [Testing Strategy](#testing-strategy)
9. [Deployment Plan](#deployment-plan)

---

## 🎯 Overview

### Objective
Build an intelligent shopping list generation system that automatically creates organized, consolidated shopping lists from meal plans, with optional price comparison across grocery stores.

### Key Features
1. **Automatic List Generation** - Extract ingredients from meal plans
2. **Smart Consolidation** - Merge duplicate ingredients with unit conversion
3. **Category Organization** - Group items by store sections
4. **Price Estimation** - Predict ingredient costs (Phase 3a)
5. **Store API Integration** - Fetch real prices (Phase 3b - optional)
6. **Manual Editing** - Add/remove/modify items
7. **Purchase Tracking** - Mark items as purchased

### Success Metrics
- List generation time: < 2 seconds
- Consolidation accuracy: > 95%
- Category classification accuracy: > 90%
- User satisfaction: 4+ stars

---

## 🔧 Functional Requirements

### FR-1: Shopping List Generation

**User Story:**  
*As a user, I want to automatically generate a shopping list from my meal plan so that I know exactly what to buy.*

**Acceptance Criteria:**
- ✅ Given a meal plan ID, extract all ingredients from associated recipes
- ✅ Scale ingredient quantities by servings
- ✅ Consolidate duplicate ingredients (e.g., "2 cups milk" + "1 cup milk" = "3 cups milk")
- ✅ Normalize ingredient names (e.g., "tomatoes" = "tomato")
- ✅ Convert units when possible (e.g., "500g flour" + "1 lb flour" = "~1.6 lbs flour")
- ✅ Return organized list grouped by category

**Priority:** P0 (Must Have)  
**Complexity:** High  
**Dependencies:** Neo4j recipe data with ingredient relationships

---

### FR-2: Category Organization

**User Story:**  
*As a user, I want my shopping list organized by store sections (produce, dairy, meat, etc.) so I can shop efficiently.*

**Acceptance Criteria:**
- ✅ Classify ingredients into standard categories:
  - Produce (fruits, vegetables)
  - Dairy & Eggs
  - Meat & Seafood
  - Bakery & Bread
  - Pantry (grains, pasta, canned goods)
  - Frozen Foods
  - Beverages
  - Spices & Condiments
- ✅ Support custom category ordering
- ✅ Handle unclassified items gracefully (default to "Other")

**Priority:** P0 (Must Have)  
**Complexity:** Medium  
**Dependencies:** Ingredient taxonomy/mapping

---

### FR-3: Unit Conversion & Consolidation

**User Story:**  
*As a user, I want duplicate ingredients automatically combined so I don't buy more than needed.*

**Acceptance Criteria:**
- ✅ Recognize equivalent ingredients (fuzzy matching):
  - "tomato" = "tomatoes"
  - "chicken breast" = "chicken breasts"
  - "olive oil" = "extra virgin olive oil"
- ✅ Convert compatible units:
  - Volume: cups ↔ liters ↔ ml ↔ fl oz
  - Weight: grams ↔ kg ↔ lbs ↔ oz
  - Count: items, cloves, stalks
- ✅ Display consolidated total in user-friendly format
- ✅ Show original recipe references (e.g., "Used in: Pasta Carbonara, Caesar Salad")

**Priority:** P0 (Must Have)  
**Complexity:** High  
**Dependencies:** Unit conversion library (pint)

---

### FR-4: Manual List Management

**User Story:**  
*As a user, I want to add extra items or remove ingredients I already have.*

**Acceptance Criteria:**
- ✅ Add custom items to list (name, quantity, category)
- ✅ Remove items from list
- ✅ Update item quantities
- ✅ Change item categories
- ✅ Mark items as "in pantry" (exclude from shopping)

**Priority:** P1 (Should Have)  
**Complexity:** Low  
**Dependencies:** None

---

### FR-5: Purchase Tracking

**User Story:**  
*As a user, I want to check off items as I shop so I don't forget anything.*

**Acceptance Criteria:**
- ✅ Mark individual items as purchased
- ✅ Unmark items if needed
- ✅ View completion percentage
- ✅ Filter to show only unpurchased items
- ✅ Clear all purchased items from list

**Priority:** P1 (Should Have)  
**Complexity:** Low  
**Dependencies:** None

---

### FR-6: Price Estimation (Phase 3a)

**User Story:**  
*As a user, I want to see estimated costs for my shopping list so I can budget accordingly.*

**Acceptance Criteria:**
- ✅ Estimate price per ingredient based on:
  - Historical average prices
  - Ingredient category
  - Quantity/unit
  - Regional adjustments (optional)
- ✅ Calculate total estimated cost
- ✅ Show cost breakdown by category
- ✅ Indicate price is an estimate

**Priority:** P1 (Should Have)  
**Complexity:** Medium  
**Dependencies:** Price database or ML model

---

### FR-7: Store Price Comparison (Phase 3b - Optional)

**User Story:**  
*As a user, I want to compare prices across different stores so I can save money.*

**Acceptance Criteria:**
- ✅ Fetch real-time prices from grocery APIs:
  - Instacart
  - Walmart
  - Kroger
- ✅ Display prices side-by-side
- ✅ Calculate total cost per store
- ✅ Recommend cheapest store
- ✅ Handle API failures gracefully (fallback to estimates)

**Priority:** P2 (Nice to Have)  
**Complexity:** High  
**Dependencies:** API partnerships, rate limits

---

### FR-8: List History & Reuse

**User Story:**  
*As a user, I want to view my past shopping lists so I can reuse them.*

**Acceptance Criteria:**
- ✅ Store completed shopping lists
- ✅ View list history (last 30 days)
- ✅ Duplicate previous list
- ✅ Archive old lists

**Priority:** P2 (Nice to Have)  
**Complexity:** Low  
**Dependencies:** None

---

## 🚀 Non-Functional Requirements

### NFR-1: Performance
- List generation: < 2 seconds for 50-item list
- API response time: < 500ms (p95)
- Database queries: < 100ms
- Handle 1000 concurrent users

### NFR-2: Scalability
- Support up to 10,000 active users
- Store 1M+ shopping lists
- Handle 100K+ ingredient variations

### NFR-3: Reliability
- 99.9% uptime
- Graceful degradation if external APIs fail
- Data consistency (ACID compliance)

### NFR-4: Security
- User lists are private (user_id isolation)
- No sensitive data in lists
- SQL injection prevention
- Rate limiting (100 req/min per user)

### NFR-5: Usability
- Clear error messages
- Intuitive categorization
- Mobile-friendly response format

---

## 🏗️ Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client (Mobile/Web)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Shopping List Router                         │   │
│  │  POST /shopping-lists/generate                           │   │
│  │  GET  /shopping-lists/                                   │   │
│  │  GET  /shopping-lists/{id}                               │   │
│  │  PUT  /shopping-lists/{id}/items/{item_id}               │   │
│  │  DELETE /shopping-lists/{id}/items/{item_id}             │   │
│  │  POST /shopping-lists/{id}/items                         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Shopping List Service Layer                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │  Ingredient      │  │   Quantity       │  │  Category    │  │
│  │  Extractor       │  │   Consolidator   │  │  Classifier  │  │
│  │                  │  │                  │  │              │  │
│  │ - Parse recipes  │  │ - Unit convert   │  │ - ML model   │  │
│  │ - Scale by       │  │ - Fuzzy match    │  │ - Keyword    │  │
│  │   servings       │  │ - Merge dupes    │  │   mapping    │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Price Service (Optional)                     │  │
│  │  ┌────────────────┐  ┌────────────────┐                  │  │
│  │  │  Price         │  │  External APIs │                  │  │
│  │  │  Estimator     │  │  - Instacart   │                  │  │
│  │  │  (ML Model)    │  │  - Walmart     │                  │  │
│  │  └────────────────┘  │  - Kroger      │                  │  │
│  │                      └────────────────┘                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  PostgreSQL      │  │  Neo4j           │                     │
│  │                  │  │                  │                     │
│  │ - shopping_lists │  │ - recipes        │                     │
│  │ - list_items     │  │ - ingredients    │                     │
│  │                  │  │ - HAS_INGREDIENT │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💾 Database Schema

### PostgreSQL Tables

```sql
-- Shopping Lists Table
CREATE TABLE shopping_lists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES meal_plans(id) ON DELETE SET NULL,
    
    name VARCHAR(255) DEFAULT 'Shopping List',
    status VARCHAR(50) DEFAULT 'active', -- active, completed, archived
    
    total_estimated_cost DECIMAL(10, 2) DEFAULT 0.0,
    total_items INTEGER DEFAULT 0,
    purchased_items INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    INDEX idx_user_id (user_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_status (status)
);

-- Shopping List Items Table
CREATE TABLE shopping_list_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    list_id UUID NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
    
    ingredient_name VARCHAR(255) NOT NULL,
    normalized_name VARCHAR(255), -- for fuzzy matching
    
    quantity DECIMAL(10, 2),
    unit VARCHAR(50),
    
    category VARCHAR(100) DEFAULT 'Other', -- produce, dairy, meat, etc.
    
    estimated_price DECIMAL(10, 2),
    store_prices JSONB, -- {"walmart": 3.99, "kroger": 4.29}
    
    is_purchased BOOLEAN DEFAULT FALSE,
    is_manual BOOLEAN DEFAULT FALSE, -- user-added vs auto-generated
    
    recipe_references TEXT[], -- array of recipe titles that use this ingredient
    
    notes TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_list_id (list_id),
    INDEX idx_category (category),
    INDEX idx_is_purchased (is_purchased)
);

-- Ingredient Category Mapping (optional, for ML training)
CREATE TABLE ingredient_categories (
    id SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(255) UNIQUE NOT NULL,
    category VARCHAR(100) NOT NULL,
    confidence DECIMAL(3, 2), -- 0.0 to 1.0
    source VARCHAR(50), -- 'manual', 'ml_model', 'keyword'
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ingredient (ingredient_name),
    INDEX idx_category (category)
);

-- Price History (for ML training - optional)
CREATE TABLE ingredient_price_history (
    id SERIAL PRIMARY KEY,
    ingredient_name VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 2),
    unit VARCHAR(50),
    
    price DECIMAL(10, 2) NOT NULL,
    store VARCHAR(100),
    location VARCHAR(255), -- zip code or city
    
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_ingredient (ingredient_name),
    INDEX idx_store (store),
    INDEX idx_recorded_at (recorded_at)
);
```

### SQLAlchemy Models

```python
# src/database/models.py

class ShoppingList(Base):
    __tablename__ = "shopping_lists"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("meal_plans.id"), nullable=True)
    
    name = Column(String(255), default="Shopping List")
    status = Column(String(50), default="active")
    
    total_estimated_cost = Column(Float, default=0.0)
    total_items = Column(Integer, default=0)
    purchased_items = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="shopping_lists")
    plan = relationship("MealPlan", back_populates="shopping_lists")
    items = relationship("ShoppingListItem", back_populates="shopping_list", cascade="all, delete-orphan")


class ShoppingListItem(Base):
    __tablename__ = "shopping_list_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    list_id = Column(UUID(as_uuid=True), ForeignKey("shopping_lists.id"), nullable=False)
    
    ingredient_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255))
    
    quantity = Column(Float)
    unit = Column(String(50))
    
    category = Column(String(100), default="Other")
    
    estimated_price = Column(Float)
    store_prices = Column(JSON)
    
    is_purchased = Column(Boolean, default=False)
    is_manual = Column(Boolean, default=False)
    
    recipe_references = Column(ARRAY(String))
    
    notes = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    shopping_list = relationship("ShoppingList", back_populates="items")
```

---

## 🔌 API Endpoints

### 1. Generate Shopping List from Meal Plan

```http
POST /shopping-lists/generate
Authorization: Bearer {token}
Content-Type: application/json

{
  "plan_id": "uuid",
  "name": "Weekly Shopping - Dec 1-7",
  "include_price_comparison": false,
  "exclude_items": ["salt", "pepper"] // items already in pantry
}

Response 201:
{
  "id": "uuid",
  "user_id": "uuid",
  "plan_id": "uuid",
  "name": "Weekly Shopping - Dec 1-7",
  "status": "active",
  "total_estimated_cost": 78.50,
  "total_items": 24,
  "purchased_items": 0,
  "items": [
    {
      "id": "uuid",
      "ingredient_name": "chicken breast",
      "normalized_name": "chicken breast",
      "quantity": 2.5,
      "unit": "lbs",
      "category": "Meat & Seafood",
      "estimated_price": 12.99,
      "is_purchased": false,
      "recipe_references": ["Grilled Chicken Salad", "Chicken Pasta"]
    },
    {
      "id": "uuid",
      "ingredient_name": "tomatoes",
      "quantity": 6,
      "unit": "items",
      "category": "Produce",
      "estimated_price": 4.50,
      "is_purchased": false,
      "recipe_references": ["Caesar Salad", "Pasta Marinara", "Bruschetta"]
    }
  ],
  "created_at": "2025-12-01T10:00:00Z"
}
```

### 2. Get All Shopping Lists

```http
GET /shopping-lists/
Authorization: Bearer {token}
Query Parameters:
  - status: active|completed|archived (optional)
  - limit: 10 (default)
  - offset: 0 (default)

Response 200:
{
  "items": [
    {
      "id": "uuid",
      "name": "Weekly Shopping - Dec 1-7",
      "status": "active",
      "total_items": 24,
      "purchased_items": 12,
      "total_estimated_cost": 78.50,
      "created_at": "2025-12-01T10:00:00Z"
    }
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}
```

### 3. Get Shopping List by ID

```http
GET /shopping-lists/{id}
Authorization: Bearer {token}

Response 200:
{
  "id": "uuid",
  "name": "Weekly Shopping - Dec 1-7",
  "status": "active",
  "total_items": 24,
  "purchased_items": 12,
  "total_estimated_cost": 78.50,
  "items_by_category": {
    "Produce": [
      {
        "id": "uuid",
        "ingredient_name": "tomatoes",
        "quantity": 6,
        "unit": "items",
        "estimated_price": 4.50,
        "is_purchased": true
      }
    ],
    "Meat & Seafood": [...],
    "Dairy & Eggs": [...]
  },
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T15:30:00Z"
}
```

### 4. Add Manual Item to List

```http
POST /shopping-lists/{id}/items
Authorization: Bearer {token}
Content-Type: application/json

{
  "ingredient_name": "ice cream",
  "quantity": 1,
  "unit": "pint",
  "category": "Frozen Foods",
  "notes": "vanilla flavor"
}

Response 201:
{
  "id": "uuid",
  "ingredient_name": "ice cream",
  "quantity": 1,
  "unit": "pint",
  "category": "Frozen Foods",
  "is_manual": true,
  "is_purchased": false,
  "notes": "vanilla flavor"
}
```

### 5. Update Shopping List Item

```http
PUT /shopping-lists/{id}/items/{item_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "is_purchased": true,
  "quantity": 2.0,
  "notes": "bought organic"
}

Response 200:
{
  "id": "uuid",
  "ingredient_name": "tomatoes",
  "quantity": 2.0,
  "is_purchased": true,
  "notes": "bought organic",
  "updated_at": "2025-12-01T16:00:00Z"
}
```

### 6. Delete Shopping List Item

```http
DELETE /shopping-lists/{id}/items/{item_id}
Authorization: Bearer {token}

Response 204: No Content
```

### 7. Mark All Items as Purchased

```http
POST /shopping-lists/{id}/complete
Authorization: Bearer {token}

Response 200:
{
  "id": "uuid",
  "status": "completed",
  "completed_at": "2025-12-01T17:00:00Z",
  "purchased_items": 24,
  "total_items": 24
}
```

### 8. Delete Shopping List

```http
DELETE /shopping-lists/{id}
Authorization: Bearer {token}

Response 204: No Content
```

---

## 📝 Implementation Plan

### Week 1: Core Infrastructure

#### Tasks
1. **Database Setup**
   - [ ] Create migration for `shopping_lists` table
   - [ ] Create migration for `shopping_list_items` table
   - [ ] Add relationships to existing models (User, MealPlan)
   - [ ] Create SQLAlchemy models
   - [ ] Add indexes

2. **Pydantic Schemas**
   - [ ] Create `src/schemas/shopping_list.py`
   - [ ] ShoppingListBase, ShoppingListCreate, ShoppingList
   - [ ] ShoppingListItemBase, ShoppingListItemCreate, ShoppingListItem
   - [ ] ShoppingListGenerateRequest
   - [ ] ShoppingListSummary

3. **Basic Service Layer**
   - [ ] Create `src/services/shopping_list_service.py`
   - [ ] Implement `extract_ingredients_from_meal_plan()`
   - [ ] Implement `create_shopping_list()`
   - [ ] Implement `get_shopping_list()`

**Deliverables:**
- Database tables created
- Basic CRUD operations working
- Unit tests for models

---

### Week 2: Consolidation & Categorization

#### Tasks
1. **Ingredient Consolidation**
   - [ ] Implement ingredient name normalization
   - [ ] Add fuzzy matching (thefuzz library)
   - [ ] Create unit conversion module (`src/utils/unit_converter.py`)
   - [ ] Implement `consolidate_ingredients()`
   - [ ] Handle edge cases (incompatible units, unknown items)

2. **Category Classification**
   - [ ] Create category mapping file (`src/data/ingredient_categories.json`)
   - [ ] Implement keyword-based classifier
   - [ ] Add ML-based classifier (optional - scikit-learn)
   - [ ] Implement `classify_ingredient_category()`
   - [ ] Add confidence scoring

3. **Recipe Reference Tracking**
   - [ ] Track which recipes use each ingredient
   - [ ] Display recipe names in list items
   - [ ] Handle duplicate references

**Deliverables:**
- Ingredient consolidation working (>90% accuracy)
- Category classification working (>85% accuracy)
- Unit tests for consolidation logic

---

### Week 3: API Endpoints & Integration

#### Tasks
1. **API Router**
   - [ ] Create `src/api/routers/shopping_lists.py`
   - [ ] Implement POST `/shopping-lists/generate`
   - [ ] Implement GET `/shopping-lists/`
   - [ ] Implement GET `/shopping-lists/{id}`
   - [ ] Implement POST `/shopping-lists/{id}/items`
   - [ ] Implement PUT `/shopping-lists/{id}/items/{item_id}`
   - [ ] Implement DELETE `/shopping-lists/{id}/items/{item_id}`
   - [ ] Implement POST `/shopping-lists/{id}/complete`

2. **Service Layer Completion**
   - [ ] Implement `add_manual_item()`
   - [ ] Implement `update_item()`
   - [ ] Implement `delete_item()`
   - [ ] Implement `mark_item_purchased()`
   - [ ] Implement `complete_list()`
   - [ ] Add proper error handling

3. **Integration with Meal Plans**
   - [ ] Add `shopping_lists` relationship to MealPlan model
   - [ ] Add "Generate Shopping List" trigger from meal plan
   - [ ] Handle meal plan updates (regenerate list?)

**Deliverables:**
- All API endpoints functional
- Integration with existing meal plan system
- Postman/API tests passing

---

### Week 4: Price Estimation & Polish

#### Tasks
1. **Price Estimation (Basic)**
   - [ ] Create price estimation database/mapping
   - [ ] Implement `estimate_ingredient_price()`
   - [ ] Add category-based pricing
   - [ ] Calculate total list cost
   - [ ] Add cost breakdown by category

2. **Testing & Documentation**
   - [ ] Write integration tests
   - [ ] Write E2E tests (pytest + httpx)
   - [ ] Update API documentation
   - [ ] Add example requests/responses
   - [ ] Create user guide

3. **Performance Optimization**
   - [ ] Add database query optimization
   - [ ] Add caching for category mappings
   - [ ] Benchmark list generation time
   - [ ] Optimize consolidation algorithm

4. **Bug Fixes & Polish**
   - [ ] Handle edge cases
   - [ ] Improve error messages
   - [ ] Add validation
   - [ ] Code review & refactoring

**Deliverables:**
- Price estimation working (±20% accuracy)
- All tests passing (>90% coverage)
- Documentation complete
- Phase 3a COMPLETE

---

### Optional: Week 5+ (Phase 3b - External APIs)

#### Tasks
1. **Grocery API Integration**
   - [ ] Set up API keys (Instacart, Walmart, Kroger)
   - [ ] Create API client wrappers
   - [ ] Implement parallel price fetching
   - [ ] Add timeout & retry logic
   - [ ] Handle API rate limits

2. **Price Comparison UI**
   - [ ] Display prices from multiple stores
   - [ ] Show cheapest store recommendation
   - [ ] Add store selection preference

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_shopping_list_service.py

def test_extract_ingredients_from_meal_plan():
    """Test ingredient extraction from recipes"""
    # Given a meal plan with 3 recipes
    # When we extract ingredients
    # Then we should get all unique ingredients with quantities

def test_consolidate_ingredients():
    """Test ingredient consolidation"""
    ingredients = [
        {"name": "tomato", "quantity": 2, "unit": "items"},
        {"name": "tomatoes", "quantity": 3, "unit": "items"},
        {"name": "cherry tomatoes", "quantity": 1, "unit": "cup"}
    ]
    # Should consolidate to ~5 items of tomatoes

def test_unit_conversion():
    """Test unit conversion"""
    # 2 cups milk + 500ml milk = ~2.5 cups milk

def test_category_classification():
    """Test ingredient categorization"""
    assert classify_category("chicken breast") == "Meat & Seafood"
    assert classify_category("tomato") == "Produce"
    assert classify_category("milk") == "Dairy & Eggs"
```

### Integration Tests
```python
# tests/test_shopping_list_api.py

async def test_generate_shopping_list_from_meal_plan():
    """E2E test for list generation"""
    # 1. Create user & meal plan
    # 2. Generate shopping list
    # 3. Verify all ingredients present
    # 4. Verify consolidation worked
    # 5. Verify categories assigned

async def test_manual_item_management():
    """Test adding/updating/removing manual items"""
    # 1. Create shopping list
    # 2. Add manual item
    # 3. Update item quantity
    # 4. Delete item
    # 5. Verify list updated correctly
```

---

## 🚀 Deployment Plan

### Prerequisites
- PostgreSQL database updated with new tables
- Environment variables configured
- API documentation updated

### Deployment Steps
1. **Database Migration**
   ```bash
   docker exec -it plate-planner-db psql -U postgres -d plateplanner
   # Run migration SQL scripts
   ```

2. **Deploy New Code**
   ```bash
   docker-compose build api
   docker-compose up -d api
   ```

3. **Verify Deployment**
   ```bash
   curl http://localhost:8000/docs
   # Check for new /shopping-lists endpoints
   ```

4. **Monitoring**
   - Check API logs for errors
   - Monitor response times
   - Track list generation success rate

---

## 📊 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| List Generation Time | < 2 sec | API response time |
| Consolidation Accuracy | > 95% | Manual verification |
| Category Accuracy | > 90% | User feedback |
| API Response Time (p95) | < 500ms | Monitoring |
| Test Coverage | > 90% | pytest-cov |
| Bug Rate | < 1 per 100 lists | Error tracking |

---

## 🎯 Acceptance Criteria

Phase 3a is complete when:
- ✅ All 8 API endpoints implemented and tested
- ✅ Ingredient consolidation working with >90% accuracy
- ✅ Category classification working with >85% accuracy
- ✅ Unit tests passing with >85% coverage
- ✅ Integration tests passing
- ✅ API documentation updated
- ✅ Performance benchmarks met (< 2 sec generation)
- ✅ Deployed to production and verified

---

## 🔜 Next Steps (Phase 4)

After Phase 3 completion:
1. **Payment Integration** - Stripe subscriptions
2. **Grocery API Integration** - Real-time pricing (Phase 3b)
3. **Mobile App** - Shopping list UI
4. **Pantry Management** - Track what user already has

---

## 📚 Resources

### Libraries
- **pint** - Unit conversion
- **thefuzz** - Fuzzy string matching
- **python-Levenshtein** - String similarity
- **scikit-learn** - ML-based category classification (optional)

### External APIs (Phase 3b)
- Instacart Connect API
- Walmart Open API
- Kroger Developer API
- Spoonacular Nutrition API

---

**Document Version:** 1.0  
**Last Updated:** November 25, 2025  
**Status:** ✅ Ready for Implementation

