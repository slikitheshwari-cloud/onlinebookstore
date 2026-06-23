from django.shortcuts import HttpResponse, render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.views import View
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from cart.cart import Cart
from .models import Order, OrderItem
from .forms import OrderCreateForm
from .pdfcreator import renderPdf
import qrcode
import os
from django.conf import settings

def order_create(request):
	cart = Cart(request)
	if request.user.is_authenticated:
		customer = get_object_or_404(User, id=request.user.id)
		form = OrderCreateForm(request.POST or None, initial={"name": customer.first_name, "email": customer.email})
		if request.method == 'POST':
			if form.is_valid():
				order = form.save(commit=False)
				order.customer = User.objects.get(id=request.user.id)
				order.payable = cart.get_total_price()
				order.totalbook = len(cart) # len(cart.cart) // number of individual book
				order.save()

				for item in cart:
					OrderItem.objects.create(
						order=order, 
						book=item['book'], 
						price=item['price'], 
						quantity=item['quantity']
						)
				# Generate QR codes
				order_qr = generate_order_qr(order)
				payment_qr = generate_payment_qr(order)

				cart.clear()

				return render(
    				request,
    				'order/successfull.html',
    				{
        				'order': order,
        				'order_qr': order_qr,
        				'payment_qr': payment_qr,
    				}
				)

			else:
				messages.error(request, "Fill out your information correctly.")

		if len(cart) > 0:
			return render(request, 'order/order.html', {"form": form})
		else:
			return redirect('store:books')
	else:
		return redirect('store:signin')
			
def order_list(request):
	my_order = Order.objects.filter(customer_id = request.user.id).order_by('-created')
	paginator = Paginator(my_order, 5)
	page = request.GET.get('page')
	myorder = paginator.get_page(page)

	return render(request, 'order/list.html', {"myorder": myorder})

def order_details(request, id):
	order_summary = get_object_or_404(Order, id=id)

	if order_summary.customer_id != request.user.id:
		return redirect('store:index')

	orderedItem = OrderItem.objects.filter(order_id=id)
	context = {
		"o_summary": order_summary,
		"o_item": orderedItem
	}
	return render(request, 'order/details.html', context)

class pdf(View):
    def get(self, request, id):
        query = get_object_or_404(Order, id=id)

        context = {
            "order": query
        }

        article_pdf = renderPdf('order/pdf.html', context)
        return HttpResponse(article_pdf, content_type='application/pdf')

def generate_order_qr(order):

    data = f"""
Order ID: 2018{order.id}
Name: {order.name}
Phone: {order.phone}
Email: {order.email}
"""

    qr = qrcode.make(data)

    os.makedirs(
        os.path.join(settings.MEDIA_ROOT, "qr"),
        exist_ok=True
    )

    filename = f"qr/order_{order.id}.png"

    qr.save(
        os.path.join(settings.MEDIA_ROOT, filename)
    )

    return filename


def generate_payment_qr(order):

    upi_id = "yourupi@paytm"

    upi_url = f"upi://pay?pa={upi_id}&pn=BookStore"

    qr = qrcode.make(upi_url)

    filename = f"qr/payment_{order.id}.png"

    qr.save(
        os.path.join(settings.MEDIA_ROOT, filename)
    )

    return filename