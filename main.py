# import requests
# import tqdm
#
# class YD:
#     def __init__(self, token):
#         self.token = token
#         self.base_url = "y0__xCClpKwBRjblgMgvu6xuRNyQiljetCEjOPtTM0ee27kVtGeNw"
#
#
#     def create_folder(self, folder_name):
#         requests.put(self.base_url + "/v1/disk/resources",
#                      headers={"Authoreization": self.token},
#                      params={"path": folder_name})
#
#     def upload_file(self, path, folder):
#
#
#
#
# disk_connector = YD()
import requests
import json
import os
from urllib.parse import urlparse
from tqdm import tqdm
import logging
from io import BytesIO
import secrets

import Kenv

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DogCEO:
    """
    Класс для работы с API dog.ceo.
    """
    def __init__(self):
        self.base_url = "https://dog.ceo/api"

    def get_breeds(self):
        """
        Получает список всех пород собак.
        """
        response = requests.get(f"{self.base_url}/breeds/list/all")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return list(data["message"].keys())
        else:
            logging.error(f"Ошибка при получении списка пород: {data['message']}")
            return None

    def get_images_by_breed(self, breed):
        """
        Получает список изображений для заданной породы.
        """
        breed = breed.replace(" ", "-")
        response = requests.get(f"{self.base_url}/breed/{breed}/images")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении изображений для породы {breed}: {data['message']}")
            return None

    def get_sub_breeds(self, breed):
        """
        Получает список подпород для заданной породы.
        """
        response = requests.get(f"{self.base_url}/breed/{breed}/list")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении списка подпород для породы {breed}: {data['message']}")
            return None

    def get_images_by_sub_breed(self, breed, sub_breed):
        """
        Получает список изображений для заданной подпороды.
        """
        response = requests.get(f"{self.base_url}/breed/{breed}/{sub_breed}/images")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении изображений для подпороды {sub_breed} породы {breed}: {data['message']}")
            return None

class YD:
    """
    Класс для работы с Яндекс.Диском.
    """
    def __init__(self, token):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.headers = {"Authorization": f"OAuth {self.token}"}

    def folder_exists(self, folder_path):
        """
        Проверяет, существует ли папка на Яндекс.Диске.
        """
        try:
            response = requests.get(
                self.base_url,
                headers=self.headers,
                params={"path": folder_path}
            )
            response.raise_for_status()
            return True  # Папка существует, если запрос успешен
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return False  # Папка не существует, если вернулась ошибка 404
            else:
                # Другие ошибки HTTP, например, проблемы с авторизацией
                logging.error(f"Ошибка при проверке существования папки '{folder_path}': {e}")
                return False


    def create_folder(self, folder_path):
        """
        Создает папку на Яндекс.Диске.
        """
        response = requests.put(
            self.base_url,
            headers=self.headers,
            params={"path": folder_path}
        )
        response.raise_for_status()
        logging.info(f"Папка '{folder_path}' успешно создана.")
        return True

    def get_upload_link(self, path):
        """
        Получает ссылку для загрузки файла на Яндекс.Диск.
        """
        response = requests.get(
            f"{self.base_url}/upload",
            headers=self.headers,
            params={"path": path, "overwrite": "true"}
        )
        response.raise_for_status()
        data = response.json()
        return data.get("href")

    def upload_file(self, file_path, file_url, image_url):
        """
        Загружает файл на Яндекс.Диск по полученной ссылке "по воздуху".
        """
        image_data = requests.get(image_url, stream=True).content
        buffer = BytesIO(image_data)
        response = requests.put(file_url, data=buffer)
        response.raise_for_status()

        if response.status_code == 201:
            logging.info(f"Файл '{file_path}' успешно загружен.")
            return True
        else:
            logging.error(f"Ошибка при загрузке файла '{file_path}'. Код ошибки: {response.status_code}")
            return False

class BackupManager:
    """
    Класс для управления резервным копированием.
    """
    def __init__(self, ya_disk, dog_ceo):
        self.ya_disk = ya_disk
        self.dog_ceo = dog_ceo
        self.results = []
        self.breed_name_mapping = {
            "Алабай": "Akbash-Dog",
            "Немецкая овчарка": "German-Shepherd",
        }

    def backup_breed(self, breed):
        """
        Выполняет резервное копирование изображений для заданной породы.
        """
        # Переводим название породы на английский (если есть в словаре)
        english_breed = self.breed_name_mapping.get(breed, breed)

        # 1. Создаем папку на Яндекс.Диске для породы (если она еще не существует)
        folder_path = breed
        if not self.ya_disk.folder_exists(folder_path):
            self.ya_disk.create_folder(folder_path)
        else:
            logging.info(f"Папка '{folder_path}' уже существует.")

        # 2. Получаем список изображений для породы (используем английское название)
        images = self.dog_ceo.get_images_by_breed(english_breed)
        if images is None:
            logging.error(f"Не удалось получить изображения для породы '{breed}' (английское название: '{english_breed}')")
            return

        # 3. Загружаем ОДНУ картинку для породы
        if images:  # Проверяем, что список не пустой
            image_url = images[0]  # Берем первую картинку
            self.upload_image(breed, image_url, folder_path)

        # 4. Проверяем наличие под-пород
        sub_breeds = self.dog_ceo.get_sub_breeds(english_breed)
        if sub_breeds:
            logging.info(f"У породы '{breed}' есть под-породы: {sub_breeds}")
            for sub_breed in sub_breeds:
                images = self.dog_ceo.get_images_by_sub_breed(english_breed, sub_breed)
                if images is None:
                    logging.error(f"Не удалось получить изображения для подпороды '{sub_breed}' породы '{breed}'")
                    continue
                # Загружаем ОДНУ картинку для каждой под-породы
                if images: # Проверяем, что список не пустой
                    image_url = images[0] # Берем первую картинку
                    self.upload_image(breed, image_url, folder_path, sub_breed=sub_breed)

    def upload_image(self, breed, image_url, folder_path, sub_breed=None):
        """
        Загружает одно изображение на Яндекс.Диск.
        """
        # 1. Формируем имя файла
        if sub_breed:
            file_name = f"{breed}_{sub_breed}_{os.path.basename(urlparse(image_url).path)}" # Добавляем sub_breed к имени файла
        else:
            file_name = f"{breed}_{os.path.basename(urlparse(image_url).path)}"
        file_path = f"{folder_path}/{file_name}"

        # 2. Получаем ссылку на загрузку
        upload_link = self.ya_disk.get_upload_link(file_path)

        # 3. Загружаем файл "по воздуху"
        if self.ya_disk.upload_file(file_path, upload_link, image_url):
            self.results.append({"file_name": file_name})
        else:
            logging.error(f"Не удалось загрузить файл '{file_name}'.")

    def save_results(self, filename="backup_results.json"):
        """
        Сохраняет информацию о загруженных файлах в JSON-файл.
        """
        with open(filename, "w") as f:
            json.dump(self.results, f, indent=2)
        logging.info(f"Результаты сохранены в файл '{filename}'.")

if __name__ == "__main__":
    TOKEN = Kenv.DISK_TOKEN

    # 2. Получаем название породы от пользователя
    breed = input("Введите название породы собаки: ")

    # 3. Создаем экземпляры классов
    ya_disk = YD(TOKEN)
    dog_ceo = DogCEO()
    backup_manager = BackupManager(ya_disk, dog_ceo)

    # 4. Выполняем резервное копирование
    backup_manager.backup_breed(breed)

    # 5. Сохраняем результаты в JSON-файл
    backup_manager.save_results()