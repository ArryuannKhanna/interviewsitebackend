from django.db import models
import json

# Create your models here.
class QuestionAnswer(models.Model):
    subject = models.CharField(max_length=255)
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return f"{self.subject}: {self.question[:50]}..."


class SessionFeedback(models.Model):
    """
    A model to store session-specific feedback and interactions for SQLite.
    """
    session_id = models.CharField(max_length=100)
    user = models.CharField(max_length=100)  # Replace with ForeignKey(User, on_delete=models.CASCADE) for actual user models
    interaction_history = models.TextField(default="[]")  # JSON-encoded string
    overall_feedback = models.TextField(null=True, blank=True)
    hr_skills = models.IntegerField(default=0)  # Rating out of 10
    communication_skills = models.IntegerField(default=0)  # Rating out of 10
    technical_skills = models.IntegerField(default=0)  # Rating out of 10

    class Meta:
        unique_together = ('session_id', 'user')  # Composite primary key

    def __str__(self):
        return f"Session: {self.session_id} | User: {self.user}"

    # Helper methods to work with JSON data
    def get_interaction_history(self):
        """
        Returns interaction history as a Python list.
        """
        return json.loads(self.interaction_history)

    def add_interaction(self, interaction):
        """
        Adds a new interaction to the history.
        """
        history = self.get_interaction_history()
        history.append(interaction)
        self.interaction_history = json.dumps(history)

    def save_interaction_history(self, history):
        """
        Saves the updated interaction history.
        """
        self.interaction_history = json.dumps(history)