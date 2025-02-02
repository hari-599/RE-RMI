from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth.models import User
from django.core.cache import cache
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import os
import pandas as pd
import threading

def process_excel_file(file_path):
    """
    Processes the uploaded Excel file and extracts dynamic cumulative values
    for each question from respective sheets, skipping the first two rows.
    """
    import re
    xls = pd.ExcelFile(file_path)

    # Map topic IDs to sheet names and response value columns
    sheets = {
        "1": {"sheet_name": "GOVERNANCE", "response_col": "GOV_Response Value"},
        "2": {"sheet_name": "MARKET CONDITIONS", "response_col": "MC_Response Value"},
        "3": {"sheet_name": "NON-PROSUMERS ", "response_col": "CP(NP)_Response Value"},
        "4": {"sheet_name": "LIVE-PROSUMERS", "response_col": "CP(LP)_Response Value"},
    }

    data = {}

    for topic_id, sheet_info in sheets.items():
        sheet_name = sheet_info["sheet_name"]
        response_col = sheet_info["response_col"]

        # Match the correct sheet, handling any trailing/leading spaces
        matched_sheet = next((s for s in xls.sheet_names if s.strip() == sheet_name.strip()), None)
        if not matched_sheet:
            raise ValueError(f"Sheet '{sheet_name}' is missing in the uploaded Excel file.")

        # Read the sheet into a DataFrame, skipping the first 2 rows
        df = xls.parse(matched_sheet, skiprows=2)

        # Clean up column names (removing extra spaces)
        df.columns = [re.sub(r"\s+", " ", col).strip() for col in df.columns]

        # Rename columns dynamically
        column_mapping = {
            "Question no.": "Question Number",
            response_col: "Cumulative Value"
        }
        df = df.rename(columns=column_mapping)

        # Select only relevant columns
        required_columns = ['Question Number', "Cumulative Value"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(
                f"Missing required column(s) {missing_columns} in sheet: {sheet_name}."
            )

        # Extract and process the required data
        sheet_data = df[required_columns].to_dict(orient='records')
        data[topic_id] = sheet_data

    return data

def delete_file_after_timeout(file_path, timeout=3600):
    """
    Deletes the file after the specified timeout.
    """
    def delete_file():
        if os.path.exists(file_path):
            os.remove(file_path)
        # Clear the contribution cache after timeout
        cache.delete(f'contribution_user_{file_path.split("_")[-1].split("/")[0]}')

    timer = threading.Timer(timeout, delete_file)
    timer.start()

@login_required
def upload_excel_view(request):
    if request.method == "POST":
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, "No file uploaded. Please select a file.")
            return redirect('home')
        if not excel_file.name.endswith(('.xls', '.xlsx')):
            messages.error(request, "Invalid file format. Please upload an Excel file.")
            return redirect('home')

        user_directory = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}')
        try:
            os.makedirs(user_directory, exist_ok=True)
        except OSError as e:
            messages.error(request, f"Error creating directory: {str(e)}")
            return redirect('home')

        file_path = os.path.join(user_directory, excel_file.name)
        try:
            with open(file_path, 'wb+') as destination:
                for chunk in excel_file.chunks():
                    destination.write(chunk)

            # Schedule file deletion after 3600 seconds
            delete_file_after_timeout(file_path)

            # Process the uploaded file
            processed_data = process_excel_file(file_path)
            cache.set(f'processed_data_user_{request.user.id}', processed_data, timeout=3600)

            # Reset the contribution cache
            cache.delete(f'contribution_user_{request.user.id}')
            messages.success(request, f"File '{excel_file.name}' processed successfully!")
            return redirect('home')

        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('home')

    return render(request, 'home.html')

def fetch_topic_data(request, topic_id):
    """
    Fetches data for a specific topic ID dynamically for template rendering.
    """
    user_directory = os.path.join(settings.MEDIA_ROOT, f'user_{request.user.id}')
    # Dynamically get the first file in the user's directory
    file_name = next((f for f in os.listdir(user_directory) if f.endswith(('.xls', '.xlsx'))), None)
    if not file_name:
        return JsonResponse({"error": "No Excel file found for the user."}, status=404)
    
    file_path = os.path.join(user_directory, file_name)

    try:
        processed_data = process_excel_file(file_path)
        topic_data = processed_data.get(topic_id, [])

        # Render the topic-specific page
        if topic_id == "1":
            return render(request, 'regional_governance.html', {'data': topic_data})
        elif topic_id == "2":
            return render(request, 'regional_market_conditions.html', {'data': topic_data})
        elif topic_id == "3":
            return render(request, 'consumer_perception.html', {'data': topic_data})
        elif topic_id == "4":
            return render(request, 'consumer_perception.html', {'data': topic_data})
        else:
            return JsonResponse({"error": "Invalid topic ID."}, status=400)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def index(request):
    return render(request, 'main/index.html')

def home_view(request):
    return render(request, 'main/home.html')

def login_view(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            cache.delete(f'processed_data_user_{user.id}')  # Clear cached data
            cache.delete(f'contribution_user_{user.id}')    # Clear calculated contribution

            # Delete the user's uploaded file upon login
            user_directory = os.path.join(settings.MEDIA_ROOT, f'user_{user.id}')
            if os.path.exists(user_directory):
                for file_name in os.listdir(user_directory):
                    file_path = os.path.join(user_directory, file_name)
                    if os.path.isfile(file_path):
                        os.remove(file_path)

            messages.success(request, "Logged in successfully!")
            return redirect('home')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('index')
    return render(request, 'index.html')

def signup_view(request):
    if request.method == "POST":
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # Validate passwords
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('index')

        # Check if username is already taken
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect('index')

        # Create the user
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created successfully! You can now log in.")
        return redirect('index')

    return render(request, 'index.html')

@login_required
def regional_governance(request):
    """
    View for rendering Governance data.
    """
    processed_data = cache.get(f'processed_data_user_{request.user.id}')
    if not processed_data:
        messages.error(request, "No processed data found. Please upload an Excel file.")
        return redirect('home')

    governance_data = processed_data.get("1", [])  # Topic ID 1 is Governance
    return render(request, 'main/regional_governance.html', {'data': governance_data})

@login_required
def regional_market_conditions(request):
    """
    View for rendering Market Conditions data.
    """
    processed_data = cache.get(f'processed_data_user_{request.user.id}')
    if not processed_data:
        messages.error(request, "No processed data found. Please upload an Excel file.")
        return redirect('home')

    market_conditions_data = processed_data.get("2", [])  # Topic ID 2 is Market Conditions
    return render(request, 'main/regional_market_conditions.html', {'data': market_conditions_data})

def consumer_perception(request):
    return render(request, 'main/consumer_perception.html')

def re_rmi_summary(request):
    return render(request, 'main/re_rmi_summary.html')

def regional_overview(request):
    if request.method == 'POST':
        x = float(request.POST.get('annual_consumption', 0))
        y = float(request.POST.get('annual_generation', 0))
        contribution = (y / x * 100) if x > 0 else 0

        # Cache the calculated contribution
        cache.set(f'contribution_user_{request.user.id}', contribution, timeout=3600)
        return JsonResponse({'contribution': contribution})

    return render(request, 'main/regional_overview.html')

def logout_view(request):
    user_id = request.user.id
    cache.delete(f'processed_data_user_{user_id}')  # Clear cached data
    cache.delete(f'contribution_user_{user_id}')    # Clear calculated contribution
    logout(request)
    messages.success(request, "Logged out successfully!")
    return redirect('index')

def get_topic_data(request, topic_id):
    # Get user-specific Excel file path
    user_id = request.user.id  # Assuming the user is authenticated
    excel_dir = os.path.join(settings.MEDIA_ROOT, f'user_{user_id}')
    # Dynamically get the first file in the user's directory
    excel_file = next((f for f in os.listdir(excel_dir) if f.endswith(('.xls', '.xlsx'))), None)
    if not excel_file:
        return JsonResponse({'error': 'File not found for the user'}, status=404)
    
    excel_file_path = os.path.join(excel_dir, excel_file)

    try:
        # Process the Excel file
        processed_data = process_excel_file(excel_file_path)
        topic_data = processed_data.get(str(topic_id), [])
        return JsonResponse(topic_data, safe=False)
    except Exception as e:
        # Handle exceptions (e.g., missing sheets/columns in Excel file)
        return JsonResponse({'error': str(e)}, status=500)

def help_view(request):
    return render(request, 'main/help.html')

