import streamlit as st
import base64
import os
import streamlit.components.v1 as components

import streamlit as st
import base64
import os
import streamlit.components.v1 as components

def run():
    st.markdown("---")
    st.title("Optiverse : A gajodhar.ai enterprise")
    st.markdown("---")

    info_text = {
        'malya' : {
            'image_path': './metadata/home/malya.png',
            'quote': '“You can call me a playboy, you can call me a thief, but don’t call me small. <br> ~Vijay Malya'

        },

        'mehta' : {
            'image_path': './metadata/home/mehta.png',
            'quote': '“Risk hai toh ishq hai." <br> ~Harshad Mehta'
        },

        'elizabeth' : {
            'image_path': './metadata/home/elizabeth.png',
            'quote': '“The minute that you have a backup plan, you’ve admitted you’re not going to succeed." <br> ~Elizabeth Holmes (Sherlocks Sister)'
        },

        'subrata' : {
            'image_path': './metadata/home/subrata.png',
            'quote': '“I have always believed in the power of the common man." <br> ~Subrata Roy'
        },

        'jordan' : {
            'image_path': './metadata/home/jordan.png',
            'quote': '“Act as if! Act as if you are a wealthy man, rich already, and then you will surely become rich." <br> ~Jordan Belfort'
        },

        'nino' : {
            'image_path': './metadata/home/nino.png',
            'quote': '“Pande ka dick is SIGNIFICANTLY bigger than mine there is no doubt about it." <br> ~NINO'
        },

        'pandoo' : {
            'image_path': './metadata/home/pandoo.png',
            'quote': '“Nino is just being kind. He is right though." <br> ~PANDOO'
        }
    }

    image_paths = []
    image_texts = []
    for key, value in info_text.items():
        image_paths.append(value['image_path'])
        image_texts.append(value['quote'])

    # Convert images to base64 for embedding
    def get_base64_of_image(img_path):
        with open(img_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()

    images_base64 = [get_base64_of_image(img) for img in image_paths]

    # Build the slides HTML dynamically
    slides_html = ""
    for i, (img_b64, text) in enumerate(zip(images_base64, image_texts)):
        active_class = "active" if i == 0 else ""
        slides_html += f"""
        <div class="mySlides {active_class}">
            <div class="slide-content">
                <div class="image-container">
                    <img src="data:image/png;base64,{img_b64}">
                </div>
                <div class="text-container">
                    <p>{text}</p>
                </div>
            </div>
        </div>
        """

    # Full HTML (with CSS + JS)
    html_code = f"""
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@1,600&display=swap" rel="stylesheet">

    <style>
    .slideshow-container {{
        position: relative;
        width: 1600px;   /* increased width */
        height: 700px;   /* increased height */
        margin: 0 auto;  /* center align */
        overflow: hidden;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }}

    .mySlides {{
        position: absolute;
        width: 100%;
        height: 100%;
        opacity: 0;
        transition: opacity 1s ease-in-out;
        display: flex;
    }}

    .mySlides.active {{
        opacity: 1;
    }}

    .slide-content {{
        display: flex;
        width: 100%;
        height: 100%;
    }}

    .image-container {{
        flex: 1;
        height: 100%;
    }}

    .image-container img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
        border-radius: 12px 0 0 12px;
    }}

    .text-container {{
        flex: 1;
        background: #fdf6f0;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
        border-radius: 0 12px 12px 0;
    }}

    .text-container p {{
        font-family: 'Playfair Display', serif;
        font-size: 28px;
        font-style: italic;
        font-weight: 600;
        text-align: center;
        color: #333;
        line-height: 1.4;
    }}
    </style>

    <div class="slideshow-container">
        {slides_html}
    </div>

    <script>
    let slideIndex = 0;
    const slides = document.getElementsByClassName("mySlides");

    function showSlides() {{
        for (let i = 0; i < slides.length; i++) {{
            slides[i].classList.remove("active");
        }}
        slideIndex++;
        if (slideIndex > slides.length) {{slideIndex = 1}}
        slides[slideIndex-1].classList.add("active");
        setTimeout(showSlides, 4000); // Change every 4 seconds
    }}
    showSlides();
    </script>
    """

    # Render inside Streamlit properly
    components.html(html_code, height=920)

