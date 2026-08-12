from django.db import models

# Create your models here.
class Parent(models.Model):
  name= models.CharField(max_length=100)
  email= models.EmailField(unique=True)
  phone= models.CharField(max_length= 20)
  created_at= models.DateTimeField(auto_now_add=True)
  
  def __str__(self):
    return self.name
  
class Skill(models.Model):
  name= models.CharField(max_length= 100, unique=True)
  
  def __str__(self):
    return self.name
  
class LSAProfile(models.Model):
  name= models.CharField(max_length=20)
  email= models.EmailField(unique=True)
  bio= models.TextField(blank=True)
  is_active= models.BooleanField(default=True)
  skills= models.ManyToManyField(Skill, related_name= "lsa_skills")
  created_at= models.DateTimeField(auto_now_add=True)
  
  def __str__(self):
    return self.name
  
class Booking(models.Model):
  class Status(models.TextChoices):
     PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
     CONFIRMED = "CONFIRMED", "Confirmed"
     PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
     CANCELLED = "CANCELLED", "Cancelled"
     COMPLETED = "COMPLETED", "Completed"
     
  parent= models.ForeignKey(
    Parent,
    on_delete= models.CASCADE,
    related_name="bookings"
  )
  
  lsa=models.ForeignKey(
    LSAProfile,
    on_delete= models.PROTECT,
    related_name= "bookings",
  )
  
  start_time=models.DateTimeField()
  end_time=models.DateTimeField()
  
  status=models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_PAYMENT)
  
  created_at= models.DateTimeField(auto_now_add=True)
  updated_at= models.DateTimeField(auto_now=True)
  
  class Meta:
    indexes= [
      models.Index(fields=["lsa", "start_time", "end_time"]),
      models.Index(fields=["status"]),
    ]
    
  def __str__(self):
    return f"Booking {self.id} - {self.lsa.name}"
  
class Payment(models.Model):
  class Status(models.TextChoices):
    PENDING="PENDING", "Pending",
    SUCCESS= "SUCCESS", "Success",
    FAILED= "FAILED","Failed"
    
  booking = models.OneToOneField(
      Booking,
      on_delete=models.CASCADE,
      related_name="payment",
  )

  transaction_id = models.CharField(
      max_length=100,
      unique=True,
  )

  amount = models.DecimalField(
      max_digits=10,
      decimal_places=2,
  )

  status = models.CharField(
      max_length=20,
      choices=Status.choices,
      default=Status.PENDING,
  )

  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  def __str__(self):
    return self.transaction_id 