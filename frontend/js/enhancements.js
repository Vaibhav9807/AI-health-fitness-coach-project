/* Daily checklist, hydration and workout-plan controls for the existing app. */
const photoUrls = {
  "meal-breakfast": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?auto=format&fit=crop&w=720&q=72",
  "meal-lunch": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=720&q=72",
  "meal-dinner": "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=720&q=72",
  "meal-snack": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=720&q=72",
  "workout-chest": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-back": "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-shoulders": "https://images.unsplash.com/photo-1534258936925-c58bed479fcb?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-arms": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-legs": "https://images.unsplash.com/photo-1517963879433-6ad2b056d712?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-abs": "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-full-body": "https://images.unsplash.com/photo-1546483875-ad9014c88eba?auto=format&fit=crop&w=560&h=360&q=72",
  "workout-cardio": "https://images.unsplash.com/photo-1552674605-db6ffd4facb5?auto=format&fit=crop&w=560&h=360&q=72"
};
const photoFallbacks = {
  "meal-breakfast": "Fresh breakfast", "meal-lunch": "Colorful healthy meal",
  "meal-dinner": "Fresh ingredients", "meal-snack": "Fruit and vegetables",
  "workout-chest": "Chest workout", "workout-back": "Back workout",
  "workout-shoulders": "Shoulder workout", "workout-arms": "Strength training",
  "workout-legs": "Leg workout", "workout-abs": "Core training",
  "workout-full-body": "Full-body workout", "workout-cardio": "Outdoor running"
};

function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function photoMarkup(key, alt, extraClass = '') {
  const src = photoUrls[key];
  if (!src) return '';
  return `<div class="photo-frame ${extraClass}" data-fallback="${esc(photoFallbacks[key] || alt)}"><img src="${esc(src)}" alt="${esc(alt)}" loading="lazy" decoding="async"></div>`;
}

document.addEventListener('error', e => {
  const image = e.target;
  if (image instanceof HTMLImageElement && image.closest('.photo-frame')) {
    image.closest('.photo-frame').classList.add('image-fallback');
    image.remove();
  }
}, true);

function renderDailyTasks(data) {
  const list = $('#daily-task-list');
  if (!list) return;
  const percent = Number(data.percentage || 0);
  $('#task-count').textContent = `${data.completed_count} of ${data.total_count} completed`;
  $('#task-percent').textContent = `${percent}%`;
  $('#task-summary').textContent = data.summary;
  $('#task-progress-bar').style.width = `${percent}%`;
  list.closest('.daily-tasks-panel').querySelector('[role="progressbar"]').setAttribute('aria-valuenow', String(percent));
  list.innerHTML = data.tasks.map(task => `<div class="daily-task-row ${task.completed ? 'is-complete' : ''}">
    <label for="daily-task-${task.id}"><input id="daily-task-${task.id}" type="checkbox" data-task-check="${task.id}" ${task.completed ? 'checked' : ''}><span>${esc(task.title)}</span></label>
    ${task.is_custom ? `<button class="task-remove" type="button" data-remove-task="${task.id}" aria-label="Remove ${esc(task.title)}">Remove</button>` : ''}
  </div>`).join('') || '<div class="empty-state">No tasks for this day.</div>';
}

function renderWater(data) {
  if (!$('#water-intake')) return;
  const goal = Number(data.goal_ml || 2000);
  const intake = Number(data.intake_ml || 0);
  const percent = Math.min(100, Number(data.percentage || 0));
  $('#water-intake').textContent = intake.toLocaleString();
  $('#water-goal-label').textContent = `${goal.toLocaleString()} ml`;
  $('#water-progress-bar').style.width = `${percent}%`;
  $('.water-track').setAttribute('aria-valuenow', String(percent));
  const goalSelect = $('#water-goal');
  if (![...goalSelect.options].some(option => Number(option.value) === goal)) {
    goalSelect.add(new Option(`${goal.toLocaleString()} ml`, String(goal)));
  }
  goalSelect.value = String(goal);
  $('#water-entry-list').innerHTML = data.entries.length ? data.entries.map(entry => `<form class="water-edit-form" data-water-entry="${entry.id}">
    <label class="sr-only" for="water-entry-${entry.id}">Correct this water entry in millilitres</label>
    <input id="water-entry-${entry.id}" name="amount_ml" type="number" min="50" max="3000" step="50" value="${entry.amount_ml}" required>
    <button class="button button-outline" type="submit">Update</button>
    <button class="button water-delete" type="button" data-delete-water="${entry.id}" aria-label="Remove ${entry.amount_ml} millilitre entry">Remove</button>
  </form>`).join('') : '<div class="empty-state">No water logged yet. Add an entry when you have a drink.</div>';
}

function renderDashboardWorkout(plans) {
  const box = $('#dashboard-workout-summary');
  const todayPlans = plans.filter(plan => plan.date === todayISO());
  box.innerHTML = todayPlans.length ? todayPlans.map(plan => `<div class="dashboard-workout-item"><b>${esc(plan.name)}</b><span>${plan.completed_count} of ${plan.total_count} exercises checked · ${plan.percentage}%</span><span>About ${plan.estimated_minutes} min</span></div>`).join('') : 'Choose a routine when you\'re ready.';
}

function renderDashboardWeek() {
  const box = $('#dashboard-week-activity');
  if (!box || !state.progress) return;
  const today = new Date(`${todayISO()}T12:00:00`);
  const monday = new Date(today);
  monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));
  const sessions = new Map((state.progress.weekly || []).map(item => [item.exercise_date, item.count]));
  const days = Array.from({ length: 7 }, (_, index) => {
    const current = new Date(monday);
    current.setDate(monday.getDate() + index);
    const key = todayISOFrom(current);
    return { key, label: current.toLocaleDateString(undefined, { weekday: 'short' }), count: sessions.get(key) || 0 };
  });
  const max = Math.max(1, ...days.map(day => day.count));
  box.innerHTML = days.map(day => `<div class="dashboard-week-day ${day.count ? 'has-session' : ''}" aria-label="${day.label}: ${day.count} logged workout${day.count === 1 ? '' : 's'}"><span>${day.count || '&nbsp;'}</span><i style="height:${day.count ? Math.max(14, Math.round(day.count / max * 100)) : 5}%"></i><b>${day.label}</b></div>`).join('');
}

function todayISOFrom(dateValue) {
  return `${dateValue.getFullYear()}-${String(dateValue.getMonth() + 1).padStart(2, '0')}-${String(dateValue.getDate()).padStart(2, '0')}`;
}

async function loadDailyFeatures() {
  try {
    const [tasks, water, plans] = await Promise.all([api('/daily-tasks'), api('/water'), api('/workout-plans')]);
    renderDailyTasks(tasks);
    renderWater(water);
    renderDashboardWorkout(plans.plans);
    renderDashboardWeek();
  } catch (error) {
    notify(error.message, true);
  }
}

function renderWorkoutCatalog(data) {
  $('#workout-recommendation').textContent = `${data.recommendation_reason} Recommended: ${data.recommended_category}.`;
  const recommended = data.recommended_category;
  $('#workout-catalog').innerHTML = data.categories.map(category => {
    const key = `workout-${category.name.toLowerCase().replaceAll(' ', '-')}`;
    const title = `${category.name} workout photo`;
    return `<button type="button" class="workout-category-card ${category.name === recommended ? 'recommended' : ''}" data-create-plan="${esc(category.name)}" aria-label="Create ${esc(category.name)} workout plan">
      ${photoMarkup(key, title)}<span class="workout-category-copy">${category.name === recommended ? '<span class="recommend-badge">Suggested for you</span>' : ''}<strong>${esc(category.name)}</strong><span>${esc(category.summary)}</span></span></button>`;
  }).join('');
}

function renderWorkoutPlan(plan) {
  const dateLabel = new Date(`${plan.date}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  const exercises = plan.exercises.map(exercise => {
    const repUnit = /hold/i.test(exercise.exercise_name) ? 'sec' : 'reps';
    return `<div class="workout-exercise ${exercise.completed ? 'is-complete' : ''}">
      <div class="exercise-top"><input class="exercise-check" type="checkbox" data-exercise-check="${exercise.id}" ${exercise.completed ? 'checked' : ''} aria-label="Mark ${esc(exercise.exercise_name)} complete"><strong>${esc(exercise.exercise_name)}</strong></div>
      <form class="exercise-edit-form" data-edit-exercise="${exercise.id}">
        <label class="exercise-name-field">Exercise name<input name="exercise_name" maxlength="120" value="${esc(exercise.exercise_name)}" required></label>
        <div class="exercise-fields">
          <label>Sets<input name="sets" type="number" min="1" max="10" value="${exercise.sets}" required></label>
          <label>${repUnit === 'sec' ? 'Hold (sec)' : 'Reps'}<input name="repetitions" type="number" min="1" max="100" value="${exercise.repetitions}" required></label>
          <label>Minutes<input name="duration_minutes" type="number" min="0" max="180" value="${exercise.duration_minutes}" required></label>
          <label>Rest (sec)<input name="rest_seconds" type="number" min="0" max="600" value="${exercise.rest_seconds}" required></label>
          <button class="button button-outline" type="submit">Save</button>
          <button class="exercise-delete" type="button" data-delete-exercise="${exercise.id}">Remove</button>
        </div>
      </form>
    </div>`;
  }).join('');
  return `<article class="panel workout-plan-card"><div class="workout-plan-heading"><div><h3>${esc(plan.name)}</h3><p>${dateLabel} · Estimated ${plan.estimated_minutes} min</p></div><button type="button" class="exercise-delete" data-delete-plan="${plan.id}">Delete plan</button></div>
    <div class="workout-plan-progress"><div><span>${plan.completed_count} complete · ${plan.remaining_count} remaining</span><b>${plan.percentage}%</b></div><div class="progress-track" role="progressbar" aria-label="${esc(plan.name)} completion" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${plan.percentage}"><span style="width:${plan.percentage}%"></span></div></div>
    <div class="exercise-list">${exercises || '<div class="empty-state">Add an exercise to this plan.</div>'}</div>
    <form class="add-exercise-form" data-add-exercise="${plan.id}">
      <label>Exercise<input name="exercise_name" maxlength="120" placeholder="Exercise name" required></label>
      <label>Sets<input name="sets" type="number" min="1" max="10" value="3" required></label>
      <label>Reps<input name="repetitions" type="number" min="1" max="100" value="10" required></label>
      <label>Minutes<input name="duration_minutes" type="number" min="0" max="180" value="0" required></label>
      <label>Rest (sec)<input name="rest_seconds" type="number" min="0" max="600" value="60" required></label>
      <button class="button button-outline" type="submit">Add exercise</button>
    </form></article>`;
}

async function loadWorkoutBuilder() {
  const list = $('#workout-plan-list');
  if (!list) return;
  try {
    const data = await api('/workout-plans');
    renderWorkoutCatalog(data);
    list.innerHTML = data.plans.length ? data.plans.map(renderWorkoutPlan).join('') : '<div class="empty-state">No saved workout plans yet. Choose a category above to get started.</div>';
  } catch (error) {
    list.innerHTML = '<div class="empty-state">Workout plans could not be loaded. Please try again.</div>';
    notify(error.message, true);
  }
}

async function refreshWater() {
  const result = await api('/water');
  renderWater(result);
}

async function createWorkoutPlan(category, button) {
  button.disabled = true;
  try {
    await api('/workout-plans', { method: 'POST', body: JSON.stringify({ category }) });
    await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
    notify(`${category} plan saved. Check off each exercise as you complete it.`);
  } catch (error) {
    notify(error.message, true);
  } finally {
    button.disabled = false;
  }
}

document.addEventListener('change', async event => {
  const checkbox = event.target;
  if (checkbox.matches('[data-task-check]')) {
    const value = checkbox.checked;
    checkbox.disabled = true;
    try {
      const data = await api(`/daily-tasks/${checkbox.dataset.taskCheck}/completion`, { method: 'PUT', body: JSON.stringify({ completed: value }) });
      renderDailyTasks(data);
      notify(value ? 'Task checked off.' : 'Task marked as not done yet.');
    } catch (error) {
      checkbox.checked = !value;
      checkbox.disabled = false;
      notify(error.message, true);
    }
  } else if (checkbox.matches('[data-exercise-check]')) {
    const value = checkbox.checked;
    checkbox.disabled = true;
    try {
      await api(`/workout-exercises/${checkbox.dataset.exerciseCheck}/completion`, { method: 'PUT', body: JSON.stringify({ completed: value }) });
      await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
      notify(value ? 'Exercise marked complete.' : 'Exercise marked as not done yet.');
    } catch (error) {
      checkbox.checked = !value;
      checkbox.disabled = false;
      notify(error.message, true);
    }
  } else if (checkbox.id === 'water-goal') {
    checkbox.disabled = true;
    try {
      const data = await api('/water/goal', { method: 'PUT', body: JSON.stringify({ goal_ml: Number(checkbox.value) }) });
      renderWater(data.water);
      notify('Today\'s water goal updated.');
    } catch (error) {
      notify(error.message, true);
    } finally {
      checkbox.disabled = false;
    }
  }
});

document.addEventListener('submit', async event => {
  const form = event.target;
  if (form.id === 'add-task-form') {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      await api('/daily-tasks', { method: 'POST', body: JSON.stringify({ title: form.elements.title.value }) });
      form.reset();
      await loadDailyFeatures();
      notify('Your task was added.');
    } catch (error) { notify(error.message, true); }
    finally { button.disabled = false; }
  } else if (form.id === 'water-form') {
    event.preventDefault();
    await addWater(Number(form.elements.amount_ml.value), form);
  } else if (form.matches('.water-edit-form')) {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    button.disabled = true;
    try {
      const data = await api(`/water/${form.dataset.waterEntry}`, { method: 'PATCH', body: JSON.stringify({ amount_ml: Number(form.elements.amount_ml.value) }) });
      renderWater(data.water);
      notify('Water entry corrected.');
    } catch (error) { notify(error.message, true); }
    finally { button.disabled = false; }
  } else if (form.matches('.exercise-edit-form')) {
    event.preventDefault();
    await saveExercise(form);
  } else if (form.matches('.add-exercise-form')) {
    event.preventDefault();
    await addExercise(form);
  }
});

async function addWater(amount, form = null) {
  try {
    const data = await api('/water', { method: 'POST', body: JSON.stringify({ amount_ml: amount }) });
    renderWater(data.water);
    if (form) form.reset();
    notify('Water intake logged.');
  } catch (error) { notify(error.message, true); }
}

async function saveExercise(form) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  const data = Object.fromEntries(new FormData(form));
  for (const key of ['sets', 'repetitions', 'duration_minutes', 'rest_seconds']) data[key] = Number(data[key]);
  try {
    await api(`/workout-exercises/${form.dataset.editExercise}`, { method: 'PATCH', body: JSON.stringify(data) });
    await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
    notify('Exercise updated.');
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
}

async function addExercise(form) {
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  const data = Object.fromEntries(new FormData(form));
  for (const key of ['sets', 'repetitions', 'duration_minutes', 'rest_seconds']) data[key] = Number(data[key]);
  try {
    await api(`/workout-plans/${form.dataset.addExercise}/exercises`, { method: 'POST', body: JSON.stringify(data) });
    await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
    notify('Exercise added to your plan.');
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; }
}

document.addEventListener('click', async event => {
  const create = event.target.closest('[data-create-plan]');
  if (create) { await createWorkoutPlan(create.dataset.createPlan, create); return; }
  const add = event.target.closest('[data-add-water]');
  if (add) { await addWater(Number(add.dataset.addWater)); return; }
  const reset = event.target.closest('#reset-daily-tasks');
  if (reset) {
    reset.disabled = true;
    try {
      const data = await api('/daily-tasks/reset', { method: 'POST' });
      renderDailyTasks(data);
      notify('Today\'s checklist is ready for a fresh start.');
    } catch (error) { notify(error.message, true); }
    finally { reset.disabled = false; }
    return;
  }
  const removeTask = event.target.closest('[data-remove-task]');
  if (removeTask) {
    try {
      await api(`/daily-tasks/${removeTask.dataset.removeTask}`, { method: 'DELETE' });
      await loadDailyFeatures();
      notify('Personal task removed.');
    } catch (error) { notify(error.message, true); }
    return;
  }
  const waterDelete = event.target.closest('[data-delete-water]');
  if (waterDelete) {
    try {
      const data = await api(`/water/${waterDelete.dataset.deleteWater}`, { method: 'DELETE' });
      renderWater(data.water);
      notify('Water entry removed.');
    } catch (error) { notify(error.message, true); }
    return;
  }
  const exerciseDelete = event.target.closest('[data-delete-exercise]');
  if (exerciseDelete) {
    try {
      await api(`/workout-exercises/${exerciseDelete.dataset.deleteExercise}`, { method: 'DELETE' });
      await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
      notify('Exercise removed.');
    } catch (error) { notify(error.message, true); }
    return;
  }
  const planDelete = event.target.closest('[data-delete-plan]');
  if (planDelete) {
    if (!confirm('Delete this workout plan and its exercise history?')) return;
    try {
      await api(`/workout-plans/${planDelete.dataset.deletePlan}`, { method: 'DELETE' });
      await Promise.all([loadWorkoutBuilder(), loadDailyFeatures()]);
      notify('Workout plan deleted.');
    } catch (error) { notify(error.message, true); }
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const today = todayISO();
  for (const id of ['workout-form', 'weight-form']) {
    const input = $(`#${id} input[type=date]`);
    if (input) input.value = today;
  }
});
