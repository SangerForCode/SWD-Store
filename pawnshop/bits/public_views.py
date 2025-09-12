# views.py
from typing import Iterable, List, Optional, Set
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from django.db.models import Count
from .models import *
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List
from django.http import JsonResponse, HttpRequest
from django.views.decorators.http import require_GET
from django.db.models import Prefetch
from django.utils.timezone import localtime
# --- helpers ---
def _sanitize_fields_generic(v, allowed):
    if not v:
        return None
    fields = {f.strip() for f in v.split(",") if f.strip()}
    return (fields & set(allowed)) or None

def _parse_bool(v: Optional[str]) -> Optional[bool]:
    if v is None: return None
    v = v.strip().lower()
    if v in {"1", "true", "t", "yes", "y"}: return True
    if v in {"0", "false", "f", "no", "n"}: return False
    return None  # invalid -> ignore

def _parse_int(v: Optional[str], default: int) -> int:
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default

def _parse_csv_ints(v: Optional[str]) -> List[int]:
    if not v: return []
    out = []
    for tok in v.split(","):
        tok = tok.strip()
        if not tok: 
            continue
        try:
            out.append(int(tok))
        except ValueError:
            continue
    return out

def _sanitize_fields(v: Optional[str]) -> Optional[Set[str]]:
    if not v: return None
    allowed = {
        "id", "name", "description", "price", "is_sold",
        "category", "campus", "hostel", "whatsapp",
        "images", "added_at", "updated_at", "seller"
    }
    fields = {f.strip() for f in v.split(",") if f.strip()}
    return (fields & allowed) or None

# views_public.py (example filename)


from .models import Item, Image, Category, Hostel, Person

# Optional (Postgres fuzzy fallback). Safe to ignore if not installed.
HAS_TRIGRAM = False

VALID_CAMPUSES = {"GOA", "HYD", "PIL", "DUB"}

def _parse_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).lower() in {"1", "true", "yes", "y", "on"}

def _parse_int(val: str | None, default: int, lo: int | None = None, hi: int | None = None) -> int:
    try:
        n = int(val) if val is not None else default
    except Exception:
        n = default
    if lo is not None: n = max(lo, n)
    if hi is not None: n = min(hi, n)
    return n

def _parse_decimal(val: str | None) -> Decimal | None:
    if val is None or val == "":
        return None
    try:
        return Decimal(val)
    except (InvalidOperation, ValueError):
        return None

def _sort_mapping(sort: str | None) -> list[str]:
    """
    Supported:
      price.asc / price.desc
      added_at.desc / added_at.asc
      updated_at.desc / updated_at.asc
      (default = price.asc)
    """
    m = (sort or "").lower()
    if m == "price.desc":    return ["-price", "-updated_at"]
    if m == "price.asc":     return ["price", "-updated_at"]
    if m == "added_at.desc": return ["-added_at"]
    if m == "added_at.asc":  return ["added_at"]
    if m == "updated_at.desc": return ["-updated_at"]
    if m == "updated_at.asc":  return ["updated_at"]
    return ["price", "-updated_at"]

def _serialize_item(it: Item) -> Dict[str, Any]:
    # Prefer hostel.campus; fallback to seller.campus
    campus = None
    if it.hostel and it.hostel.campus:
        campus = it.hostel.campus
    elif it.seller and it.seller.campus:
        campus = it.seller.campus

    imgs: List[str] = []
    for img in getattr(it, "_prefetched_images", []) or []:
        try:
            imgs.append(img.image.url)
        except Exception:
            continue

    return {
        "id": it.id,
        "name": it.name,
        "description": it.description,
        "price": str(it.price),  # keep as string to avoid float issues
        "is_sold": it.is_sold,
        "whatsapp": it.whatsapp,
        "category_id": it.category_id,
        "added_at": localtime(it.added_at).isoformat(),
        "updated_at": localtime(it.updated_at).isoformat(),
        "hostel": it.hostel.name if it.hostel else None,
        "campus": campus,
        "seller_id": it.seller_id,
        "images": imgs,
    }

@require_GET
def public_api_items(request: HttpRequest) -> JsonResponse:
    """
    GET /public/api/items

    Query params:
      - is_sold=true|false     (default: false)
      - category_id=<int>
      - campus=GOA|HYD|PIL|DUB (invalid values 400)
      - hostel=<name>          (iexact)
      - seller_id=<int>
      - min_price=<decimal>    (skip freebies/garbage)
      - max_price=<decimal>
      - q=<string>             (single-text search on name/description)
      - q_any=a,b,c            (multi-term OR search across tokens)
      - name_only=true|false   (when q/q_any set; default false → name OR description)
      - fuzzy=true|false       (Postgres Trigram fallback if q/q_any present and no hits)
      - sort=price.asc|price.desc|added_at.desc|added_at.asc|updated_at.desc|updated_at.asc
      - limit=<int>            (1..50, default 12)
      - offset=<int>           (>=0, default 0)

    Response:
      {
        "items": [ ... ],
        "total": <int>,           # total matching (without limit/offset)
        "next_offset": <int|null> # for paging
      }
    """
    qs = Item.objects.select_related("seller", "category", "hostel")
    # Prefetch images in correct order into a private attribute for fast serialize
    prefetch_images = Prefetch(
        "images",
        queryset=Image.objects.all().order_by("display_order", "id"),
        to_attr="_prefetched_images",
    )
    qs = qs.prefetch_related(prefetch_images)

    # --- Filters ---
    is_sold = _parse_bool(request.GET.get("is_sold"), default=False)
    if is_sold:
        qs = qs.filter(is_sold=True)
    else:
        qs = qs.filter(is_sold=False)

    cat_id = request.GET.get("category_id")
    if cat_id:
        try:
            qs = qs.filter(category_id=int(cat_id))
        except Exception:
            pass

    campus = request.GET.get("campus")
    if campus:
        campus = campus.upper()
        if campus not in VALID_CAMPUSES:
            return JsonResponse({"error": "Invalid campus. Use one of GOA|HYD|PIL|DUB."}, status=400)
        # Match either by item's hostel campus or seller campus (whichever is set)
        qs = qs.filter(
            Q(hostel__campus=campus) | Q(seller__campus=campus)
        )

    hostel = request.GET.get("hostel")
    if hostel:
        qs = qs.filter(hostel__name__iexact=hostel.strip())

    seller_id = request.GET.get("seller_id")
    if seller_id:
        try:
            qs = qs.filter(seller_id=int(seller_id))
        except Exception:
            pass

    # Price band
    min_price = _parse_decimal(request.GET.get("min_price"))
    if min_price is not None:
        qs = qs.filter(price__gte=min_price)
    max_price = _parse_decimal(request.GET.get("max_price"))
    if max_price is not None:
        qs = qs.filter(price__lte=max_price)

    # --- Search ---
    name_only = _parse_bool(request.GET.get("name_only"), default=False)
    q = (request.GET.get("q") or "").strip()
    q_any = (request.GET.get("q_any") or "").strip()

    if q:
        # single-term search
        if name_only:
            qs = qs.filter(Q(name__icontains=q))
        else:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))

    if q_any:
        # multi-term OR search
        # supports "a,b,c" (commas)
        tokens = [t.strip() for t in q_any.split(",") if t.strip()]
        if tokens:
            qobj = Q()
            for t in tokens:
                if name_only:
                    qobj |= Q(name__icontains=t)
                else:
                    qobj |= Q(name__icontains=t) | Q(description__icontains=t)
            qs = qs.filter(qobj)

    # Optional fuzzy rescue if nothing matched AND you asked for it
    if _parse_bool(request.GET.get("fuzzy"), default=False) and (q or q_any):
        try:
            if HAS_TRIGRAM and not qs.exists():
                # Use a combined string for similarity (name field)
                seed = q if q else q_any.replace(",", " ")
                qs = (Item.objects
                      .annotate(sim=TrigramSimilarity("name", seed))
                      .filter(sim__gt=0.2, is_sold=is_sold)
                      .order_by("-sim"))
                # Re-apply basic price range if given
                if min_price is not None:
                    qs = qs.filter(price__gte=min_price)
                if max_price is not None:
                    qs = qs.filter(price__lte=max_price)
        except Exception:
            pass

    # --- Sorting, paging ---
    sort = request.GET.get("sort")
    qs = qs.order_by(*_sort_mapping(sort))

    limit = _parse_int(request.GET.get("limit"), default=12, lo=1, hi=50)
    offset = _parse_int(request.GET.get("offset"), default=0, lo=0)

    total = qs.count()
    page = list(qs[offset: offset + limit])

    items = [_serialize_item(it) for it in page]
    next_offset = offset + limit if (offset + limit) < total else None

    return JsonResponse(
        {"items": items, "total": total, "next_offset": next_offset},
        json_dumps_params={"ensure_ascii": False}
    )

@require_GET
def public_api_categories(request):
    """
    GET /api/categories
      q: fuzzy match on name
      sort: name.asc|name.desc|added_at.desc (default: name.asc)
      limit, offset or page
      fields: id,name,item_count,icon_class,added_at
    """
    q = (request.GET.get("q") or "").strip()
    sort = (request.GET.get("sort") or "name.asc").lower()
    sort_map = {
        "name.asc": "name",
        "name.desc": "-name",
        "added_at.desc": "-added_at",
    }
    order_by = sort_map.get(sort, "name")

    limit = _parse_int(request.GET.get("limit"), 50)
    limit = 1 if limit < 1 else 200 if limit > 200 else limit
    if request.GET.get("offset") is not None:
        offset = max(_parse_int(request.GET.get("offset"), 0), 0)
    else:
        page = max(_parse_int(request.GET.get("page"), 1), 1)
        offset = (page - 1) * limit

    fields = _sanitize_fields_generic(
        request.GET.get("fields"),
        allowed=["id", "name", "item_count", "icon_class", "added_at"],
    )

    qs = Category.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs.order_by(order_by, "id")

    total = qs.count()
    cats = list(qs[offset : offset + limit])

    def ser(c: Category):
        data = {
            "id": c.id,
            "name": c.name,
            "item_count": c.item_count,   # your denormalized field
            "icon_class": c.icon_class,
            "added_at": c.added_at,
        }
        if fields:
            data = {k: v for k, v in data.items() if k in fields}
        return data

    payload = [ser(c) for c in cats]
    next_offset = offset + limit if (offset + limit) < total else None
    return JsonResponse(
        {"categories": payload, "total": total, "next_offset": next_offset},
        json_dumps_params={"ensure_ascii": False, "default": str},
    )

@require_GET
def public_api_hostels(request):
    """
    GET /api/hostels
      campus: GOA|HYD|PIL|DUB|OTHERS (optional; if omitted, returns all)
      counts: true|false (default false) -> include active_items count
      q: fuzzy match on hostel name (optional)
      limit, offset or page
      fields: name,campus,active_items
    """
    campus = request.GET.get("campus")
    counts = (request.GET.get("counts") or "").strip().lower() in {"1","true","t","yes","y"}
    q = (request.GET.get("q") or "").strip()

    limit = _parse_int(request.GET.get("limit"), 100)
    limit = 1 if limit < 1 else 500 if limit > 500 else limit
    if request.GET.get("offset") is not None:
        offset = max(_parse_int(request.GET.get("offset"), 0), 0)
    else:
        page = max(_parse_int(request.GET.get("page"), 1), 1)
        offset = (page - 1) * limit

    fields = _sanitize_fields_generic(
        request.GET.get("fields"),
        allowed=["name", "campus", "active_items"],
    )

    qs = Hostel.objects.all()
    if campus:
        campus_code = campus.strip().upper()
        valid = {c[0] for c in Campus.choices}
        if campus_code not in valid:
            return JsonResponse({"error": {"code": 400, "message": "invalid campus"}}, status=400)
        qs = qs.filter(campus=campus_code)
    if q:
        qs = qs.filter(name__icontains=q)

    if counts:
        qs = qs.annotate(active_items=Count("items", filter=Q(items__is_sold=False)))

    qs = qs.order_by("name")

    total = qs.count()
    hostels = list(qs[offset : offset + limit])

    def ser(h: Hostel):
        row = {
            "name": h.name,
            "campus": h.campus,
        }
        if counts:
            row["active_items"] = getattr(h, "active_items", 0)
        if fields:
            row = {k: v for k, v in row.items() if k in fields}
        return row

    payload = [ser(h) for h in hostels]
    next_offset = offset + limit if (offset + limit) < total else None
    return JsonResponse(
        {"hostels": payload, "total": total, "next_offset": next_offset},
        json_dumps_params={"ensure_ascii": False, "default": str},
    )

from django.shortcuts import get_object_or_404

def _item_campus(item):
    if item.hostel_id and item.hostel and item.hostel.campus:
        return item.hostel.campus
    return item.seller.campus if item.seller_id else None

def _serialize_item_public(item, fields=None):
    data = {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": float(item.price),
        "is_sold": item.is_sold,
        "category": {
            "id": item.category_id,
            "name": item.category.name if item.category_id and item.category else None,
        },
        "campus": _item_campus(item),
        "hostel": item.hostel.name if item.hostel_id and item.hostel else None,
        "whatsapp": item.whatsapp,
        "images": [im.image.url for im in sorted(item.images.all(), key=lambda x: x.display_order)],
        "added_at": item.added_at,
        "updated_at": item.updated_at,
        "seller": {
            "id": item.seller_id,
            "name": item.seller.name if item.seller_id and item.seller else None,
        },
    }
    if fields:
        data = {k: v for k, v in data.items() if k in fields}
    return data

@require_GET
def public_api_item_detail(request, item_id: int):
    """
    GET /api/items/<item_id>
      fields: same top-level projection as list endpoint
    """
    fields = _sanitize_fields_generic(
        request.GET.get("fields"),
        allowed=["id","name","description","price","is_sold","category","campus","hostel","whatsapp","images","added_at","updated_at","seller"],
    )
    item = get_object_or_404(
        Item.objects.select_related("category", "seller", "hostel").prefetch_related("images"),
        pk=item_id,
    )
    payload = _serialize_item_public(item, fields)
    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "default": str})

@require_GET
def public_api_campuses(_request):
    """
    GET /api/campuses
    """
    data = [{"code": code, "name": label} for code, label in Campus.choices]
    return JsonResponse({"campuses": data})
