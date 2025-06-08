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
from io import BytesIO  # Для загрузки "по воздуху"

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
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
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

        response = requests.get(f"{self.base_url}/breed/{breed}/images")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении изображений для породы {breed}: {data['message']}")
            return None



    def get_sub_breeds(self, breed):

        response = requests.get(f"{self.base_url}/breed/{breed}/list")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении списка под-пород для породы {breed}: {data['message']}")
            return None



    def get_images_by_sub_breed(self, breed, sub_breed):
        """
        Получает список изображений для заданной под-породы.
        """

        response = requests.get(f"{self.base_url}/breed/{breed}/{sub_breed}/images")
        response.raise_for_status()
        data = response.json()
        if data["status"] == "success":
            return data["message"]
        else:
            logging.error(f"Ошибка при получении изображений для под-породы {sub_breed} породы {breed}: {data['message']}")
            return None



class YD:
    """
    Класс для работы с Яндекс.Диском.
    """
    def __init__(self, token):
        self.token = token
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.headers = {"Authorization": f"OAuth {self.token}"}

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



    def upload_file(self, file_path, file_url, image_url):  # Добавлен image_url
        """
        Загружает файл на Яндекс.Диск по полученной ссылке "по воздуху".
        """


        image_data = requests.get(image_url, stream=True).content # Получаем контент картинки
        buffer = BytesIO(image_data) #  Оборачиваем в BytesIO
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

    def backup_breed(self, breed):
        """
        Выполняет резервное копирование изображений для заданной породы.
        """
        # 1. Создаем папку на Яндекс.Диске для породы
        folder_path = breed  # Имя папки = названию породы
        self.ya_disk.create_folder(folder_path)


        # 2. Получаем список изображений для породы
        images = self.dog_ceo.get_images_by_breed(breed)


        # 3. Загружаем каждое изображение на Яндекс.Диск
        for image_url in tqdm(images, desc=f"Загрузка {breed}"):
            self.upload_image(breed, image_url, folder_path)

        # 4. Проверяем наличие под-пород
        sub_breeds = self.dog_ceo.get_sub_breeds(breed)
        if sub_breeds:
            logging.info(f"У породы '{breed}' есть под-породы: {sub_breeds}")
            for sub_breed in sub_breeds:
                images = self.dog_ceo.get_images_by_sub_breed(breed, sub_breed)

                for image_url in tqdm(images, desc=f"Загрузка {breed} - {sub_breed}"):
                    self.upload_image(breed, image_url, folder_path)

    def upload_image(self, breed, image_url, folder_path):
        """
        Загружает одно изображение на Яндекс.Диск.
        """
        # 1. Формируем имя файла
        file_name = f"{breed}_{os.path.basename(urlparse(image_url).path)}"
        file_path = f"{folder_path}/{file_name}"

        # 2. Получаем ссылку на загрузку
        upload_link = self.ya_disk.get_upload_link(file_path)


        # 3. Загружаем файл "по воздуху"
        if self.ya_disk.upload_file(file_path, upload_link, image_url):  # Передаем image_url
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
    # 1. Получаем токен от пользователя
    TOKEN = os.environ.get("DISK_TOKEN")
    if not TOKEN:
        TOKEN = input("Введите ваш токен с Яндекс.Диска: ")

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