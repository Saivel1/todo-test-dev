import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from apps.tasks.models import Task, Category


@pytest.mark.django_db
class TestTaskAPI:
    """Тесты для Task API"""
    
    def test_list_tasks(self, authenticated_client, multiple_tasks):
        """Тест получения списка задач"""
        response = authenticated_client.get('/api/tasks/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        assert len(response.data['results']) == 5
    
    def test_list_tasks_unauthorized(self, api_client):
        """Тест списка задач без аутентификации"""
        response = api_client.get('/api/tasks/')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_list_tasks_only_own(self, authenticated_client, user, another_user, category):
        """Тест что пользователь видит только свои задачи"""
        # Создаём задачи для текущего пользователя
        Task.objects.create(user=user, title='My task 1')
        Task.objects.create(user=user, title='My task 2')
        
        # Создаём задачи для другого пользователя
        Task.objects.create(user=another_user, title='Other task 1')
        Task.objects.create(user=another_user, title='Other task 2')
        
        response = authenticated_client.get('/api/tasks/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 2  # Только свои задачи
        
        # Проверяем что все задачи принадлежат текущему пользователю
        for task in response.data['results']:
            assert 'My task' in task['title']
    
    def test_create_task(self, authenticated_client, category):
        """Тест создания задачи"""
        data = {
            'title': 'Новая задача',
            'description': 'Описание новой задачи',
            'deadline': (timezone.now() + timedelta(days=1)).isoformat(),
            'category_ids': [str(category.id)]
        }
        
        response = authenticated_client.post('/api/tasks/', data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Новая задача'
        assert len(response.data['categories']) == 1
        
        # Проверяем что задача создана в БД
        task = Task.objects.get(id=response.data['id'])
        assert task.title == 'Новая задача'
        assert task.categories.count() == 1
    
    def test_create_task_minimal(self, authenticated_client):
        """Тест создания задачи с минимальными данными"""
        response = authenticated_client.post('/api/tasks/', {
            'title': 'Минимальная задача'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Минимальная задача'
        assert response.data['status'] == 'pending'
    
    def test_create_task_without_title(self, authenticated_client):
        """Тест создания задачи без названия"""
        response = authenticated_client.post('/api/tasks/', {
            'description': 'Только описание'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'title' in response.data
    
    def test_get_task_detail(self, authenticated_client, task):
        """Тест получения деталей задачи"""
        response = authenticated_client.get(f'/api/tasks/{task.id}/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(task.id)
        assert response.data['title'] == task.title
    
    def test_get_other_user_task(self, authenticated_client, another_user):
        """Тест что нельзя получить чужую задачу"""
        other_task = Task.objects.create(
            user=another_user,
            title='Чужая задача'
        )
        
        response = authenticated_client.get(f'/api/tasks/{other_task.id}/')
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_update_task(self, authenticated_client, task):
        """Тест обновления задачи"""
        response = authenticated_client.patch(f'/api/tasks/{task.id}/', {
            'title': 'Обновлённое название',
            'status': 'in_progress'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Обновлённое название'
        assert response.data['status'] == 'in_progress'
        
        # Проверяем в БД
        task.refresh_from_db()
        assert task.title == 'Обновлённое название'
        assert task.status == Task.Status.IN_PROGRESS
    
    def test_delete_task(self, authenticated_client, task):
        """Тест удаления задачи"""
        task_id = task.id
        
        response = authenticated_client.delete(f'/api/tasks/{task_id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Task.objects.filter(id=task_id).exists()
    
    def test_complete_task(self, authenticated_client, task):
        """Тест отметки задачи как выполненной"""
        response = authenticated_client.post(f'/api/tasks/{task.id}/complete/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'
        
        task.refresh_from_db()
        assert task.status == Task.Status.COMPLETED
    
    def test_cancel_task(self, authenticated_client, task):
        """Тест отмены задачи"""
        response = authenticated_client.post(f'/api/tasks/{task.id}/cancel/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'
    
    def test_get_overdue_tasks(self, authenticated_client, user):
        """Тест получения просроченных задач"""
        # Создаём просроченную задачу
        overdue_task = Task.objects.create(
            user=user,
            title='Просроченная',
            deadline=timezone.now() - timedelta(days=1),
            status=Task.Status.PENDING
        )
        
        # Создаём актуальную задачу
        Task.objects.create(
            user=user,
            title='Актуальная',
            deadline=timezone.now() + timedelta(days=1)
        )
        
        response = authenticated_client.get('/api/tasks/overdue/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['id'] == str(overdue_task.id)
    
    def test_filter_tasks_by_status(self, authenticated_client, multiple_tasks):
        """Тест фильтрации задач по статусу"""
        response = authenticated_client.get('/api/tasks/my/?status=pending')
        
        assert response.status_code == status.HTTP_200_OK
        # В multiple_tasks 3 задачи с pending (0, 2, 4)
        # Но response.data может быть paginated или нет
        if 'results' in response.data:
            # Paginated response
            assert response.data['count'] == 3
        else:
            # Non-paginated response
            assert len(response.data) == 3
    
    def test_filter_tasks_by_category(self, authenticated_client, user, category):
        """Тест фильтрации по категории"""
        # Создаём задачу с категорией
        task_with_cat = Task.objects.create(user=user, title='С категорией')
        task_with_cat.categories.add(category)
        
        # Создаём задачу без категории
        Task.objects.create(user=user, title='Без категории')
        
        response = authenticated_client.get(f'/api/tasks/my/?category={category.id}')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1


@pytest.mark.django_db
class TestCategoryAPI:
    """Тесты для Category API"""
    
    def test_list_categories(self, authenticated_client, category):
        """Тест получения списка категорий"""
        Category.objects.create(name='Личное', color='#123456')
        Category.objects.create(name='Учёба', color='#654321')
        
        response = authenticated_client.get('/api/categories/')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 3
    
    def test_create_category(self, authenticated_client):
        """Тест создания категории"""
        response = authenticated_client.post('/api/categories/', {
            'name': 'Новая категория',
            'color': '#ABCDEF'
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Новая категория'
        assert response.data['color'] == '#ABCDEF'
    
    def test_create_category_duplicate_name(self, authenticated_client, category):
        """Тест создания категории с дублирующимся именем"""
        response = authenticated_client.post('/api/categories/', {
            'name': category.name,
            'color': '#000000'
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_update_category(self, authenticated_client, category):
        """Тест обновления категории"""
        response = authenticated_client.patch(f'/api/categories/{category.id}/', {
            'color': '#FFFFFF'
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['color'] == '#FFFFFF'
    
    def test_delete_category(self, authenticated_client, category):
        """Тест удаления категории"""
        category_id = category.id
        
        response = authenticated_client.delete(f'/api/categories/{category_id}/')
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Category.objects.filter(id=category_id).exists()