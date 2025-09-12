# views.py
from typing import Iterable, List, Optional, Set
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.db.models import Q
from django.db.models import Count
from .models import *

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

# --- main view ---
@require_GET
def public_api_items(request):
    """
    GET /api/items
    Query params:
      - is_sold: true|false
      - category_id: int or comma-list
      - campus: GOA|HYD|PIL|DUB|OTHERS
      - hostel: exact hostel name
      - q: free-text (name/description)
      - sort: price.asc|price.desc|added_at.asc|added_at.desc|updated_at.asc|updated_at.desc
      - limit: 1..100 (default 20)
      - offset: >=0 (default 0) ; or page: >=1 (ignored if offset given)
      - fields: comma list of top-level keys to include
    """
    # Filters
    is_sold = _parse_bool(request.GET.get("is_sold"))
    category_ids = _parse_csv_ints(request.GET.get("category_id"))
    campus = request.GET.get("campus")
    hostel = request.GET.get("hostel")
    q = request.GET.get("q")

    # Sorting
    sort = (request.GET.get("sort") or "updated_at.desc").lower()
    sort_map = {
        "price.asc": "price",
        "price.desc": "-price",
        "added_at.asc": "added_at",
        "added_at.desc": "-added_at",
        "updated_at.asc": "updated_at",
        "updated_at.desc": "-updated_at",
    }
    order_by = sort_map.get(sort, "-updated_at")

    # Pagination
    limit = _parse_int(request.GET.get("limit"), 20)
    if limit < 1: limit = 1
    if limit > 100: limit = 100
    if request.GET.get("offset") is not None:
        offset = max(_parse_int(request.GET.get("offset"), 0), 0)
    else:
        page = max(_parse_int(request.GET.get("page"), 1), 1)
        offset = (page - 1) * limit

    # Field projection
    fields = _sanitize_fields(request.GET.get("fields"))

    # Base queryset with efficient relations
    qs = (
        Item.objects.select_related("category", "seller", "hostel")
        .prefetch_related("images")
        .all()
    )

    if is_sold is not None:
        qs = qs.filter(is_sold=is_sold)

    if category_ids:
        qs = qs.filter(category_id__in=category_ids)

    # Campus filter: prefer item's hostel.campus; fallback to seller.campus
    if campus:
        campus = campus.strip().upper()
        valid_codes = {c[0] for c in Campus.choices}
        if campus in valid_codes:
            qs = qs.filter(Q(hostel__campus=campus) | Q(seller__campus=campus))
        else:
            return JsonResponse({"error": {"code": 400, "message": "invalid campus"}}, status=400)

    if hostel:
        qs = qs.filter(hostel__name=hostel)

    if q:
        q_ic = q.strip()
        qs = qs.filter(
            Q(name__icontains=q_ic)
            | Q(description__icontains=q_ic)
            | Q(category__name__icontains=q_ic)
        )

    qs = qs.order_by(order_by, "-id")

    total = qs.count()
    items = list(qs[offset : offset + limit])

    def campus_of_item(item) -> Optional[str]:
        if item.hostel_id and item.hostel and item.hostel.campus:
            return item.hostel.campus
        return item.seller.campus if item.seller_id else None

    def serialize_item(item) -> dict:
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
            "campus": campus_of_item(item),
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

    payload_items = [serialize_item(it) for it in items]

    next_offset = offset + limit if (offset + limit) < total else None
    resp = {
        "items": payload_items,
        "total": total,
        "next_offset": next_offset,
    }
    return JsonResponse(resp, json_dumps_params={"ensure_ascii": False, "default": str})

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
