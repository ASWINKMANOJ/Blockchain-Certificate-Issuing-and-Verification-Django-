# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from web3 import Web3
from django.http import HttpResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO

from .models import Account, Certificate
from .forms import LoginForm, AuthorizeOrgForm, IssueCertificateForm
from hexbytes import HexBytes

# ✅ blockchain.py functions
from .blockchain import (
    authorize_issuer_onchain,
    issue_certificate_onchain,
    verify_certificate_onchain
)




# ------------------------------------------------------------
# ✅ LOGIN VIEW
# ------------------------------------------------------------
def login_user(request):
    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]

        user = authenticate(request, email=email, password=password)

        if user:
            login(request, user)

            if user.role == "OWNER":
                return redirect("owner_dashboard")
            else:
                return redirect("organization_dashboard")

        messages.error(request, "Invalid email or password")

    return render(request, "authentication/login.html", {"form": form})



# ------------------------------------------------------------
# ✅ OWNER DASHBOARD
# Can auth/revoke orgs + view all orgs + view all certificates
# ------------------------------------------------------------
@login_required
def owner_dashboard(request):

    # Only contract owner allowed
    if request.user.role != "OWNER":
        return redirect("organization_dashboard")

    form = AuthorizeOrgForm(request.POST or None)
    message = ""
    blockchain_message = ""

    if request.method == "POST" and form.is_valid():
        org_email = form.cleaned_data["org_email"]

        try:
            org = Account.objects.get(email=org_email)
            print("Found org account:", org.email, org.blockchain_address, org.is_authorized, request.user.private_key)

            if org.role != "ORGANIZATION":
                message = "This account is not an organization."
            else:
                # ---------------------------------------------------
                # ✅ BLOCKCHAIN: AUTHORIZE on-chain
                # ---------------------------------------------------
                try:
                    tx_hash = authorize_issuer_onchain(
                    owner_address=request.user.blockchain_address,
                    owner_private_key=request.user.private_key,
                    org_address=org.blockchain_address
                    )
                    print("hello")

                    # mark as authorized in DB
                    org.is_authorized = True
                    org.save()

                    blockchain_message = f"On-chain Authorization Success. TX: {tx_hash}"
                    message = f"{org_email} is now an authorized issuer."

                except Exception as e:
                    blockchain_message = f"Blockchain error: {str(e)}"
                    print("error")

        except Account.DoesNotExist:
            message = "Organization account does not exist."

    # lists for UI
    authorized_orgs = Account.objects.filter(role="ORGANIZATION", is_authorized=True)
    pending_orgs = Account.objects.filter(role="ORGANIZATION", is_authorized=False)

    certificates = Certificate.objects.all().order_by("-issued_date")

    return render(request, "authentication/owner_dashboard.html", {
        "form": form,
        "message": message,
        "blockchain_message": blockchain_message,
        "authorized_orgs": authorized_orgs,
        "pending_orgs": pending_orgs,
        "certificates": certificates,
    })



# ------------------------------------------------------------
# ✅ ORGANIZATION DASHBOARD
# Must be authorized to issue certificates
# ------------------------------------------------------------
@login_required
def organization_dashboard(request):

    if request.user.role != "ORGANIZATION":
        return redirect("owner_dashboard")

    # Orgs must be authorized by OWNER before issuing certificate
    if not request.user.is_authorized:
        return render(request, "authentication/organization_dashboard.html", {
            "not_authorized": True
        })

    form = IssueCertificateForm(request.POST or None)
    message = ""
    blockchain_message = ""

    if request.method == "POST" and form.is_valid():

        certificate_id = form.cleaned_data["certificate_id"]
        recipient = form.cleaned_data["recipient_name"]
        course = form.cleaned_data["course_name"]

        # ------------------------------------------------------------
        # ✅ create the certificate metadata hash (SHA256)
        # this matches your smart contract's logic: send only dataHash
        # ------------------------------------------------------------
        raw_data = f"{certificate_id}|{recipient}|{course}|{request.user.blockchain_address}"

        # ✅ Step 1: compute bytes32 keccak hash
        hash_bytes = Web3.solidity_keccak(['string'], [raw_data])

        # ✅ Step 2: convert to HexBytes (strict bytes32 type)
        data_hash_bytes32 = HexBytes(hash_bytes)

        # ------------------------------------------------------------
        # ✅ BLOCKCHAIN: Issue certificate on-chain
        # ------------------------------------------------------------
        try:
            tx_hash = issue_certificate_onchain(
                org_address=request.user.blockchain_address,
                org_private_key=request.user.private_key,
                certificate_id=certificate_id,
                data_hash_bytes32=data_hash_bytes32
            )

            # ------------------------------------------------------------
            # ✅ Save metadata in database
            # ------------------------------------------------------------
            Certificate.objects.create(
                certificate_id=certificate_id,
                recipient_name=recipient,
                course_name=course,
                issued_by=request.user,
                blockchain_hash="0x" + hash_bytes.hex(),
                transaction_hash=tx_hash
            )

            message = "Certificate issued successfully!"
            blockchain_message = f"Blockchain TX: {tx_hash}"

        except Exception as e:
            blockchain_message = f"Blockchain error: {str(e)}"


    issued_certificates = Certificate.objects.filter(issued_by=request.user).order_by("-issued_date")

    return render(request, "authentication/organization_dashboard.html", {
        "form": form,
        "message": message,
        "blockchain_message": blockchain_message,
        "issued_certificates": issued_certificates,
        "not_authorized": False
    })



# ------------------------------------------------------------
# ✅ CERTIFICATE VERIFICATION VIEW
# Anyone can verify by entering certificate ID + metadata
# ------------------------------------------------------------
from django.shortcuts import render
from .models import Certificate
from web3 import Web3


def verify_certificate(request):

    context = {}

    if request.method == "POST":
        certificate_id = request.POST.get("certificate_id")

        # ✅ Fetch from DB
        try:
            cert = Certificate.objects.select_related("issued_by").get(
                certificate_id=certificate_id
            )

            # ✅ Certificate found → show its details
            context.update({
                "found": True,
                "certificate": cert,
            })

        except Certificate.DoesNotExist:
            # ❌ Certificate NOT found
            context["not_found"] = True

    return render(request, "authentication/verify_certificate.html", context)

def print_certificate_pdf(request, certificate_id):
    try:
        cert = Certificate.objects.select_related("issued_by").get(
            certificate_id=certificate_id
        )
    except Certificate.DoesNotExist:
        return HttpResponse("Certificate not found", status=404)

    # Create the PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c5282'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Title
    title = Paragraph("CERTIFICATE OF COMPLETION", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Certificate ID (centered)
    cert_id_text = Paragraph(f"<b>Certificate ID:</b> {cert.certificate_id}", heading_style)
    elements.append(cert_id_text)
    elements.append(Spacer(1, 0.5*inch))
    
    # Main certificate text
    recipient_style = ParagraphStyle(
        'Recipient',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    elements.append(Paragraph("This is to certify that", recipient_style))
    elements.append(Spacer(1, 0.2*inch))
    
    name_style = ParagraphStyle(
        'Name',
        parent=styles['Normal'],
        fontSize=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a5490'),
        spaceAfter=12
    )
    elements.append(Paragraph(cert.recipient_name, name_style))
    elements.append(Spacer(1, 0.2*inch))
    
    elements.append(Paragraph("has successfully completed", recipient_style))
    elements.append(Spacer(1, 0.2*inch))
    
    course_style = ParagraphStyle(
        'Course',
        parent=styles['Normal'],
        fontSize=18,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        spaceAfter=12
    )
    elements.append(Paragraph(cert.course_name, course_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Details table
    data = [
        ['Issued Date:', cert.issued_date.strftime('%B %d, %Y')],
        ['Issued By:', cert.issued_by.email],
    ]
    
    table = Table(data, colWidths=[2*inch, 4*inch])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Blockchain verification info
    verification_style = ParagraphStyle(
        'Verification',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_LEFT
    )
    
    elements.append(Paragraph("<b>Blockchain Verification:</b>", verification_style))
    elements.append(Spacer(1, 0.1*inch))
    
    hash_text = f"<b>Hash:</b> {cert.blockchain_hash[:64]}..."
    elements.append(Paragraph(hash_text, verification_style))
    
    tx_text = f"<b>Transaction:</b> {cert.transaction_hash[:64]}..."
    elements.append(Paragraph(tx_text, verification_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{cert.certificate_id}.pdf"'
    response.write(pdf)
    
    return response