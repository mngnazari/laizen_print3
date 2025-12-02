import os
import numpy as np
import trimesh
import pyrender
from PIL import Image
import math


def process_stl_files(folder_path):
    """
    پردازش تمام فایل‌های STL در فولدر مشخص شده و تبدیل آن‌ها به JPG
    """

    # بررسی وجود فولدر
    if not os.path.exists(folder_path):
        print(f"فولدر {folder_path} وجود ندارد!")
        return

    # پیدا کردن تمام فایل‌های STL
    stl_files = [f for f in os.listdir(folder_path) if f.lower().endswith('.stl')]

    if not stl_files:
        print("هیچ فایل STL در فولدر پیدا نشد!")
        return

    print(f"{len(stl_files)} فایل STL پیدا شد. شروع پردازش...")

    for i, stl_file in enumerate(stl_files, 1):
        try:
            stl_path = os.path.join(folder_path, stl_file)
            jpg_path = os.path.join(folder_path, os.path.splitext(stl_file)[0] + '.jpg')

            print(f"[{i}/{len(stl_files)}] پردازش {stl_file}...")

            # رندر کردن STL به JPG
            render_stl_to_jpg(stl_path, jpg_path)

            print(f"✓ ذخیره شد: {os.path.basename(jpg_path)}")

        except Exception as e:
            print(f"✗ خطا در پردازش {stl_file}: {str(e)}")

    print("پردازش تمام شد!")


def render_stl_to_jpg(stl_path, output_path, image_size=800):
    """
    رندر کردن فایل STL به تصویر JPG
    """

    # بارگذاری مدل STL
    mesh = trimesh.load(stl_path)

    # اگر مدل چندین قسمت دارد، آن‌ها را ترکیب کنید
    if isinstance(mesh, trimesh.Scene):
        mesh = mesh.dump().sum()

    # ایجاد صحنه pyrender
    scene = pyrender.Scene(ambient_light=[0.2, 0.2, 0.2], bg_color=[1.0, 1.0, 1.0])

    # ایجاد material سبز برای مدل (مثل پیش‌نمایش ویندوز)
    material = pyrender.MetallicRoughnessMaterial(
        metallicFactor=0.1,
        roughnessFactor=0.8,
        baseColorFactor=[0.2, 0.7, 0.2, 1.0]  # سبز مات
    )

    # اضافه کردن مدل به صحنه با material سبز
    mesh_node = pyrender.Mesh.from_trimesh(mesh, material=material)
    scene.add(mesh_node)

    # محاسبه مرکز و اندازه مدل
    bounds = mesh.bounds
    center = mesh.centroid
    size = np.max(bounds[1] - bounds[0])

    # محاسبه فاصله دوربین برای پر کردن کادر
    # فاصله بر اساس اندازه مدل و زاویه دید دوربین محاسبه می‌شود
    fov = math.radians(50)  # زاویه دید 50 درجه (مثل پیش‌نمایش ویندوز)
    distance = size / (2 * math.tan(fov / 2)) * 1.1  # ضریب 1.1 برای حاشیه مناسب

    # تنظیم موقعیت دوربین (مثل پیش‌نمایش ویندوز)
    # زاویه مشابه آنچه در پیش‌نمایش ویندوز می‌بینید
    camera_pos = center + np.array([
        distance * 0.8,  # جانبی
        -distance * 0.6,  # عمق
        distance * 0.6  # ارتفاع
    ])

    # ایجاد دوربین پرسپکتیو
    camera = pyrender.PerspectiveCamera(yfov=fov, aspectRatio=1.0)

    # محاسبه ماتریس نگاه دوربین
    # دوربین به مرکز مدل نگاه می‌کند
    camera_pose = look_at(camera_pos, center, np.array([0, 0, 1]))

    # اضافه کردن دوربین به صحنه
    scene.add(camera, pose=camera_pose)

    # اضافه کردن نور اصلی (مثل نور پیش‌نمایش ویندوز)
    light = pyrender.DirectionalLight(color=np.ones(3), intensity=2.5)
    light_pose = look_at(
        center + np.array([distance * 0.5, -distance * 0.8, distance * 0.8]),
        center,
        np.array([0, 0, 1])
    )
    scene.add(light, pose=light_pose)

    # نور پشتیبان نرم‌تر
    fill_light = pyrender.DirectionalLight(color=np.ones(3), intensity=1.0)
    fill_light_pose = look_at(
        center + np.array([-distance * 0.3, distance * 0.5, distance * 0.3]),
        center,
        np.array([0, 0, 1])
    )
    scene.add(fill_light, pose=fill_light_pose)

    # رندر کردن صحنه
    renderer = pyrender.OffscreenRenderer(image_size, image_size)
    color, _ = renderer.render(scene)

    # تبدیل به تصویر PIL و ذخیره به عنوان JPG
    img = Image.fromarray(color)
    img.save(output_path, 'JPEG', quality=95)

    # پاک کردن renderer
    renderer.delete()


def look_at(eye, target, up):
    """
    ایجاد ماتریس نگاه دوربین
    eye: موقعیت دوربین
    target: نقطه‌ای که دوربین به آن نگاه می‌کند
    up: بردار بالا
    """
    forward = target - eye
    forward = forward / np.linalg.norm(forward)

    right = np.cross(forward, up)
    right = right / np.linalg.norm(right)

    up = np.cross(right, forward)
    up = up / np.linalg.norm(up)

    # ایجاد ماتریس تبدیل
    pose = np.eye(4)
    pose[:3, 0] = right
    pose[:3, 1] = up
    pose[:3, 2] = -forward
    pose[:3, 3] = eye

    return pose


if __name__ == "__main__":
    # مسیر فولدر حاوی فایل‌های STL
    folder_path = r"C:\Users\Laser\Desktop\output"

    print("شروع پردازش فایل‌های STL...")
    process_stl_files(folder_path)