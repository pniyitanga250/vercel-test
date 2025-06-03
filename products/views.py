from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category

def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()

    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))
    
    if category_id:
        products = products.filter(category__id=category_id)
    
    context = {
        'products': products,
        'categories': categories,
        'search_query': query,
        'selected_category': category_id,
    }
    
    # If the request is AJAX, return only the product grid partial.
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'products/_product_grid.html', context)
    
    return render(request, 'products/products.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {
        'product': product,
        'product_id': pk,  # For Order Now link.
    })
