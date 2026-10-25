const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const state={user:null,profile:null,workouts:[],progress:null,charts:{},authMode:'register',page:'overview'};
const pageNames={overview:'Overview',profile:'My profile',workouts:'Workouts',progress:'Progress',nutrition:'Nutrition',coach:'Ask your coach'};
const goalNames={weight_loss:'Weight loss',weight_gain:'Weight gain',muscle_building:'Muscle building',general_fitness:'General fitness',maintain:'Maintain current weight'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function api(path,options={}){
  const res=await fetch('/api'+path,{credentials:'same-origin',headers:{'Content-Type':'application/json',...(options.headers||{})},...options});
  let data={};
  try{data=await res.json()}catch{}
  if(!res.ok)throw new Error(data.error||'Something went wrong. Please try again.');
  return data;
}

function notify(msg,error=false){
  const box=$('#notice');
  box.textContent=msg;
  box.classList.toggle('error',error);
  box.classList.remove('hidden');
  clearTimeout(notify.timer);
  notify.timer=setTimeout(()=>box.classList.add('hidden'),3800);
}

function checkPasswordStrength(pw){
  if(!pw)return{score:0,class:'',text:'Use 10 or more characters with mixed letters and numbers.'};
  let score=0;
  if(pw.length>=10)score++;
  if(pw.length>=14)score++;
  if(/[0-9]/.test(pw))score++;
  if(/[A-Z]/.test(pw)&&/[a-z]/.test(pw))score++;
  if(/[^A-Za-z0-9]/.test(pw))score++;
  if(score<=1)return{score:1,class:'weak',text:'Weak password · add numbers and varied case.'};
  if(score<=3)return{score:2,class:'medium',text:'Good password · meets safety guidelines.'};
  return{score:3,class:'strong',text:'Strong password · very secure.'};
}

function openAuth(mode){
  state.authMode=mode;
  updateAuthModal();
  $('#auth-modal').classList.remove('hidden');
  $('#auth-error').textContent='';
  $('#auth-form').reset();
  const bar=$('#strength-bar');if(bar){bar.style.width='0%';bar.className='';}
  const help=$('#password-help');if(help)help.textContent='Use 10 or more characters with mixed letters and numbers.';
}

function updateAuthModal(){
  const isReg=state.authMode==='register';
  $$('.auth-tabs button').forEach(b=>b.classList.toggle('selected',b.dataset.authTab===state.authMode));
  $('#auth-title').textContent=isReg?'Make it yours.':'Welcome back.';
  $('#auth-copy').textContent=isReg?'Create a private space for your everyday progress.':'Pick up where you left off.';
  $('#auth-submit').innerHTML=isReg?'Create my account <span>↗</span>':'Log in to my space <span>↗</span>';
  $('#auth-eyebrow').textContent=isReg?'YOUR NEXT CHAPTER':'GOOD TO HAVE YOU BACK';
  
  const fn=$('#field-fullname');if(fn)fn.classList.toggle('hidden',!isReg);
  const cp=$('#field-confirm-password');if(cp)cp.classList.toggle('hidden',!isReg);
  const str=$('#password-strength-container');if(str)str.classList.toggle('hidden',!isReg);
  const ex=$('#login-extra-links');if(ex)ex.classList.toggle('hidden',isReg);

  const pwInput=$('#auth-modal input[name=password]');
  if(pwInput){
    pwInput.autocomplete=isReg?'new-password':'current-password';
    pwInput.minLength=isReg?10:1;
  }
}

function showApp(){ $('#landing').classList.add('hidden');$('#app').classList.remove('hidden');setPage(state.page) }
function showLanding(){ $('#app').classList.add('hidden');$('#landing').classList.remove('hidden') }

function setPage(name){
  if(!pageNames[name])return;
  state.page=name;
  $$('.page').forEach(p=>p.classList.toggle('active',p.id==='page-'+name));
  $$('.nav-item[data-page]').forEach(b=>b.classList.toggle('active',b.dataset.page===name));
  $('#page-title').textContent=pageNames[name];
  $('.sidebar').classList.remove('open');
  if(name==='progress')loadProgress();
  if(name==='workouts')loadWorkouts();
  if(name==='nutrition')loadDiet();
  if(name==='overview')loadOverview();
}

function profileForm(p){
  const form=$('#profile-form');
  for(const [k,v] of Object.entries(p||{})){
    if(form.elements[k])form.elements[k].value=v??'';
  }
}

function getUserInitials(name, email){
  if(name&&name.trim()){
    const parts=name.trim().split(/\s+/);
    if(parts.length>1)return (parts[0][0]+parts[parts.length-1][0]).toUpperCase();
    return parts[0].slice(0,2).toUpperCase();
  }
  if(email)return email.slice(0,2).toUpperCase();
  return 'U';
}

async function refresh(){
  const d=await api('/me');
  state.user=d.user;
  state.profile=d.profile;
  profileForm(d.profile);

  const form=$('#profile-form');
  if(form.elements['full_name'])form.elements['full_name'].value=d.user.full_name||'';
  const emailDisplay=$('#profile-email');
  if(emailDisplay)emailDisplay.value=d.user.email;

  const displayName=d.user.full_name||d.user.display_name||'Friend';
  const initials=getUserInitials(d.user.full_name,d.user.email);
  $('#side-email').textContent=displayName;
  $('#avatar').textContent=initials;
  $('#top-profile').textContent=initials;
  $('#greeting-name').textContent=displayName;

  $('#today').textContent=new Intl.DateTimeFormat(undefined,{weekday:'short',month:'short',day:'numeric'}).format(new Date());
  await loadOverview();
  await updateMetrics();
}

function profilePayload(){
  const f=$('#profile-form');
  const p={};
  new FormData(f).forEach((v,k)=>{p[k]=v});
  for(const k of ['age','height_cm','weight_kg','workout_minutes'])p[k]=p[k]?Number(p[k]):null;
  return p;
}

async function updateMetrics(){
  const r=await api('/health-metrics',{method:'POST',body:JSON.stringify({})}).catch(e=>({error:e.message}));
  if(r.error){
    $('#metrics-results').innerHTML=`<div class="calc-row"><span>Complete age, height, weight, and sex to calculate.</span><b>—</b></div>`;
    $('#stat-bmi').textContent='—';
    $('#stat-calories').innerHTML='— <small>kcal</small>';
    return;
  }
  const m=r.metrics;
  $('#metrics-results').innerHTML=`<div class="calc-row"><span>BMI · screening measure</span><b>${m.bmi}</b></div><div class="calc-row"><span>Basal metabolic rate</span><b>${m.bmr} kcal</b></div><div class="calc-row"><span>Estimated daily energy</span><b>${m.tdee} kcal</b></div><div class="calc-row"><span>Suggested goal range</span><b>${m.calorie_range[0]}–${m.calorie_range[1]}</b></div>`;
  $('#stat-bmi').textContent=m.bmi;
  $('#stat-calories').innerHTML=`${m.tdee.toLocaleString()} <small>kcal</small>`;
  if(state.profile?.weight_kg)$('#stat-weight').innerHTML=`${Number(state.profile.weight_kg).toFixed(1)} <small>kg</small>`;
}

async function loadOverview(){
  try{
    const [r,p,rec]=await Promise.all([api('/workouts'),api('/progress'),api('/recommendations')]);
    state.workouts=r.workouts;
    state.progress=p;
    $('#stat-workouts').innerHTML=`${p.workouts_this_week} <small>sessions</small>`;
    const recent=r.workouts.slice(0,3);
    $('#recent-activity').innerHTML=recent.length?recent.map(w=>`<div class="activity-row"><span class="activity-glyph">↗</span><div><b>${esc(w.exercise_type)}</b><small>${w.duration_minutes} minutes</small></div><span class="activity-time">${shortDate(w.exercise_date)}</span></div>`).join(''):'<div class="empty-state">Your logged workouts will show up here.</div>';
    $('#focus-copy').textContent=rec.recommendations.daily;
    $('#focus-habit').textContent=rec.recommendations.progress_note;
    $('#goal-title').textContent=goalNames[state.profile?.goal]||'Set a goal that feels right.';
    $('#goal-copy').textContent=`${rec.recommendations.sessions_per_week} manageable sessions each week. ${rec.recommendations.activity_note} ${rec.recommendations.recovery}`;
    renderWeightChart(p.weights,'weightChart','weight-empty');
    if(p.weights.length)$('#weight-helper').textContent=`${p.weights.length} check-in${p.weights.length===1?'':'s'} saved`;
    else $('#weight-helper').textContent='Add your starting point';
    if(state.profile?.weight_kg)$('#stat-weight').innerHTML=`${Number(state.profile.weight_kg).toFixed(1)} <small>kg</small>`;
    else $('#stat-weight').innerHTML='— <small>kg</small>';
    await loadDailyFeatures();
  }catch(e){notify(e.message,true)}
}

function shortDate(s){
  const d=new Date(s+'T12:00:00');
  return new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric'}).format(d);
}

function renderWeightChart(items,id,emptyId){
  const canvas=$('#'+id),empty=$('#'+emptyId);
  if(!canvas)return;
  if(state.charts[id])state.charts[id].destroy();
  empty.classList.toggle('show',!items.length);
  if(!items.length)return;
  state.charts[id]=new Chart(canvas,{
    type:'line',
    data:{
      labels:items.map(x=>shortDate(x.record_date)),
      datasets:[{data:items.map(x=>x.weight_kg),borderColor:'#4d8b73',backgroundColor:'rgba(127,177,145,.12)',fill:true,tension:.35,pointRadius:3,pointBackgroundColor:'#4d8b73',borderWidth:2}]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${c.parsed.y} kg`}}},
      scales:{x:{grid:{display:false},ticks:{color:'#929b9d',font:{size:12}}},y:{grid:{color:'#f0f2f0'},ticks:{color:'#929b9d',font:{size:12}},beginAtZero:false}}
    }
  });
}

function renderWeekly(items){
  const el=$('#weeklyChart');
  if(!el)return;
  const now=new Date(),monday=new Date(now);
  monday.setDate(now.getDate()-((now.getDay()+6)%7));
  const days=Array.from({length:7},(_,i)=>{const d=new Date(monday);d.setDate(monday.getDate()+i);return d});
  const counts=days.map(d=>items.filter(w=>w.exercise_date===todayISOFrom(d)).length);
  $('#weekly-empty').classList.toggle('show',items.length===0);
  if(state.charts.weeklyChart)state.charts.weeklyChart.destroy();
  if(!items.length)return;
  state.charts.weeklyChart=new Chart(el,{
    type:'bar',
    data:{
      labels:days.map(d=>d.toLocaleDateString(undefined,{weekday:'short'})),
      datasets:[{data:counts,backgroundColor:counts.map(n=>n?'#77a98b':'#edf0ec'),borderRadius:6,maxBarThickness:34}]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{x:{grid:{display:false},ticks:{color:'#84908d',font:{size:12}}},y:{beginAtZero:true,ticks:{stepSize:1,color:'#929b9d',font:{size:12}},grid:{color:'#f0f2f0'}}}
    }
  });
}

async function loadWorkouts(){
  try{
    const [d,rp,ms]=await Promise.all([api('/workouts'),api('/recommendations'),api('/model-status')]);
    state.workouts=d.workouts;
    renderWeekly(d.workouts);
    $('#weekly-plan').innerHTML=rp.recommendations.weekly_schedule.map((item,i)=>`<div class="plan-row"><span>${String(i+1).padStart(2,'0')}</span><b>${esc(item)}</b></div>`).join('');
    $('#model-state').textContent=ms.available?'Evaluated dataset model':'No validated model';
    $('#model-note').textContent=ms.note;
    $('#dataset-predict-form').classList.toggle('hidden',!ms.available);
    $('#workout-history').innerHTML=d.workouts.length?d.workouts.map(w=>`<div class="history-row">
      <span class="activity-glyph">↗</span>
      <div class="row-main"><b>${esc(w.exercise_type)}</b><small>${w.duration_minutes} min${w.notes?' · '+esc(w.notes):''}</small></div>
      <time>${shortDate(w.exercise_date)}</time>
      <div class="history-actions">
        <button class="edit-row-btn" data-edit-workout="${w.id}" aria-label="Edit workout">✎</button>
        <button class="delete-row" data-delete-workout="${w.id}" aria-label="Delete workout">×</button>
      </div>
    </div>`).join(''):'<div class="empty-state">No workouts yet. Your first session can be a short walk.</div>';
    await loadWorkoutBuilder();
  }catch(e){notify(e.message,true)}
}

async function loadProgress(){
  try{
    const s=$('#filter-start').value,e=$('#filter-end').value;
    const query=s||e?`?start=${encodeURIComponent(s||'0001-01-01')}&end=${encodeURIComponent(e||'9999-12-31')}`:'';
    const d=await api('/progress'+query);
    state.progress=d;
    renderWeightChart(d.weights,'progressChart','progress-empty');
    $('#weight-count').textContent=`${d.weights.length} check-in${d.weights.length===1?'':'s'}`;
    const week=$('#week-list');
    const now=new Date(),mon=new Date(now);
    mon.setDate(now.getDate()-((now.getDay()+6)%7));
    const counts=Array.from({length:7},(_,i)=>{const day=new Date(mon);day.setDate(mon.getDate()+i);const key=todayISOFrom(day);return {key,name:day.toLocaleDateString(undefined,{weekday:'short'}),count:d.weekly.find(x=>x.exercise_date===key)?.count||0}});
    $('#week-summary').textContent=`${d.workouts_this_week} session${d.workouts_this_week===1?'':'s'} logged`;
    week.innerHTML=counts.map(x=>`<div class="week-day ${x.count?'has-session':''}"><b>${x.name}</b><span>${x.count?x.count+' session'+(x.count===1?'':'s'):'—'}</span></div>`).join('');
  }catch(e){notify(e.message,true)}
}

async function loadDiet(){
  try{
    const d=await api('/diet-plan'),p=d.plan;
    $('#meal-grid').innerHTML=p.meals.length?p.meals.map(m=>`<article class="meal-card">${photoMarkup('meal-'+(String(m.meal).toLowerCase().includes('snack')?'snack':String(m.meal).toLowerCase()),String(m.meal)+' meal suggestion','meal-photo')}<span class="meal-label">${esc(m.meal.toUpperCase())}</span><h3>${esc(m.name)}</h3><div class="meal-cal">${m.calories} <small>kcal · approximate</small></div><div class="macro-tags"><span>${m.protein}g protein</span><span>${m.carbs}g carbs</span><span>${m.fat}g fat</span></div></article>`).join(''):'<div class="panel empty-state">No matching meals with the current restriction filters. Review your profile restrictions.</div>';
    $('#meal-calories').innerHTML=`${p.totals.calories.toLocaleString()} <small>kcal</small>`;
    $('#macro-list').innerHTML=['protein','carbs','fat'].map(k=>`<div><span>${k[0].toUpperCase()+k.slice(1)}</span><b>${p.totals[k]} g</b></div>`).join('');
    let note=p.note;
    if(p.calorie_range){
      const midpoint=Math.round((p.calorie_range[0]+p.calorie_range[1])/2),difference=p.totals.calories-midpoint;
      note+=` Estimated goal range: ${p.calorie_range[0].toLocaleString()}–${p.calorie_range[1].toLocaleString()} kcal. This sample menu is ${Math.abs(difference).toLocaleString()} kcal ${difference<0?"below":"above"} its midpoint; portions can be adjusted to suit you. This is context, not a prescribed intake.`;
    }else{
      note+=' Complete your age, height, weight, and sex in your profile to compare against an estimated calorie range.';
    }
    $('#meal-note').textContent=note;
  }catch(e){notify(e.message,true)}
}

function addChat(text,who){
  const box=$('#chat-messages'),item=document.createElement('div');
  item.className='chat-msg '+who;
  const icon=document.createElement('span');
  icon.textContent=who==='assistant'?'✳':'•';
  const p=document.createElement('p');
  p.textContent=text;
  item.append(icon,p);
  box.append(item);
  box.scrollTop=box.scrollHeight;
  return item;
}

async function sendChat(text){
  if(!text.trim())return;
  addChat(text,'user');
  const form=$('#chat-form');
  form.elements.message.value='';
  form.querySelector('button').disabled=true;
  const load=addChat('Thinking…','assistant');
  load.classList.add('thinking');
  try{
    const d=await api('/chat',{method:'POST',body:JSON.stringify({message:text})});
    load.querySelector('p').textContent=d.reply;
    $('.chat-top small').innerHTML=`<i></i> General guidance · ${d.source==='openai'?'OpenAI':'Rule-based'}`;
  }catch(e){
    load.querySelector('p').textContent=e.message;
  }finally{
    form.querySelector('button').disabled=false;
  }
}

async function checkResetToken(){
  const params=new URLSearchParams(window.location.search);
  const token=params.get('reset_token');
  if(!token)return;
  try{
    const res=await api('/verify-reset-token?token='+encodeURIComponent(token));
    if(res.valid){
      $('#reset-token-input').value=token;
      $('#reset-copy').textContent=`Choose a new password for ${res.email}.`;
      $('#reset-modal').classList.remove('hidden');
    }else{
      openAuth('login');
      $('#auth-error').textContent=res.error||'Reset link is invalid or expired.';
    }
  }catch(e){
    openAuth('login');
    $('#auth-error').textContent=e.message;
  }
}

async function start(){
  await checkResetToken();
  try{
    await refresh();
    showApp();
  }catch{
    showLanding();
  }
}

document.addEventListener('click',async e=>{
  const auth=e.target.closest('[data-open-auth]');
  if(auth){
    e.preventDefault();
    openAuth(auth.dataset.openAuth);
    return;
  }
  const close=e.target.closest('[data-close]');
  if(close){
    close.closest('.modal').classList.add('hidden');
    return;
  }
  const tab=e.target.closest('[data-auth-tab]');
  if(tab){
    state.authMode=tab.dataset.authTab;
    updateAuthModal();
    $('#auth-error').textContent='';
    return;
  }
  const nav=e.target.closest('[data-page]');
  if(nav){
    setPage(nav.dataset.page);
    return;
  }
  const del=e.target.closest('[data-delete-workout]');
  if(del){
    if(!confirm('Delete this workout record?'))return;
    try{
      await api('/workouts/'+del.dataset.deleteWorkout,{method:'DELETE'});
      notify('Workout removed.');
      await loadWorkouts();
      await loadOverview();
    }catch(err){notify(err.message,true)}
    return;
  }
  const editW=e.target.closest('[data-edit-workout]');
  if(editW){
    const record=state.workouts.find(w=>String(w.id)===String(editW.dataset.editWorkout));
    if(record){
      const form=$('#edit-workout-form');
      form.elements.id.value=record.id;
      form.elements.exercise_type.value=record.exercise_type;
      form.elements.duration_minutes.value=record.duration_minutes;
      form.elements.exercise_date.value=record.exercise_date;
      form.elements.notes.value=record.notes||'';
      $('#edit-workout-error').textContent='';
      $('#edit-workout-modal').classList.remove('hidden');
    }
    return;
  }
  const toggleBtn=e.target.closest('.toggle-password');
  if(toggleBtn){
    const wrapper=toggleBtn.closest('.password-wrapper');
    const input=wrapper?.querySelector('input');
    if(input){
      const isPw=input.type==='password';
      input.type=isPw?'text':'password';
      toggleBtn.textContent=isPw?'🙈':'👁';
      toggleBtn.setAttribute('aria-label',isPw?'Hide password':'Show password');
    }
    return;
  }
  const forgotLink=e.target.closest('#forgot-password-link');
  if(forgotLink){
    $('#auth-modal').classList.add('hidden');
    $('#forgot-modal').classList.remove('hidden');
    $('#forgot-status').textContent='';
    $('#dev-reset-box').classList.add('hidden');
    return;
  }
  const backToLogin=e.target.closest('#back-to-login');
  if(backToLogin){
    $('#forgot-modal').classList.add('hidden');
    openAuth('login');
    return;
  }
  const menuButton=e.target.closest('#mobile-menu');
  if(menuButton){
    const opened=$('.sidebar').classList.toggle('open');
    menuButton.setAttribute('aria-expanded',String(opened));
    menuButton.setAttribute('aria-label',opened?'Close navigation':'Open navigation');
  }
  if(e.target.closest('#settings-shortcut')||e.target.closest('#top-profile'))setPage('profile');
  if(e.target.closest('#delete-account')){$('#confirm-modal').classList.remove('hidden');$('#delete-error').textContent=''}
  if(e.target.closest('#clear-chat'))$('#chat-messages').innerHTML='<div class="chat-msg assistant"><span>✳</span><p>Hi there. What would you like to work on today?</p></div>';
  const prompt=e.target.closest('.quick-prompts button');
  if(prompt)sendChat(prompt.textContent);
});

// Password strength meter updates
document.addEventListener('input', e=>{
  if(e.target.matches('#auth-form input[name=password]')){
    const res=checkPasswordStrength(e.target.value);
    const bar=$('#strength-bar'), help=$('#password-help');
    if(bar){
      bar.className=res.class;
      bar.style.width=res.score===1?'33%':res.score===2?'66%':res.score===3?'100%':'0%';
    }
    if(help)help.textContent=res.text;
  }
  if(e.target.matches('#reset-form input[name=password]')){
    const res=checkPasswordStrength(e.target.value);
    const bar=$('#reset-strength-bar'), help=$('#reset-password-help');
    if(bar){
      bar.className=res.class;
      bar.style.width=res.score===1?'33%':res.score===2?'66%':res.score===3?'100%':'0%';
    }
    if(help)help.textContent=res.text;
  }
});

// Registration and Login Form
$('#auth-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget;
  $('#auth-error').textContent='';
  const submitBtn=$('#auth-submit');
  submitBtn.disabled=true;
  const originalText=submitBtn.innerHTML;
  submitBtn.textContent='Please wait…';

  const data={
    email:f.elements.email.value,
    password:f.elements.password.value
  };
  if(state.authMode==='register'){
    data.full_name=f.elements.full_name?.value||'';
    data.confirm_password=f.elements.confirm_password?.value||'';
    if(!data.full_name.trim()){
      $('#auth-error').textContent='Please enter your full name.';
      submitBtn.disabled=false;
      submitBtn.innerHTML=originalText;
      return;
    }
    if(data.password!==data.confirm_password){
      $('#auth-error').textContent='Passwords do not match.';
      submitBtn.disabled=false;
      submitBtn.innerHTML=originalText;
      return;
    }
  }

  try{
    await api('/'+state.authMode,{method:'POST',body:JSON.stringify(data)});
    $('#auth-modal').classList.add('hidden');
    await refresh();
    showApp();
    notify(state.authMode==='register'?'Your private space is ready. Welcome!':'Welcome back.');
  }catch(err){
    $('#auth-error').textContent=err.message;
  }finally{
    submitBtn.disabled=false;
    submitBtn.innerHTML=originalText;
  }
});

// Forgot Password Form
$('#forgot-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget;
  const status=$('#forgot-status');
  const btn=$('#forgot-submit');
  btn.disabled=true;
  status.textContent='Sending link…';
  try{
    const res=await api('/forgot-password',{method:'POST',body:JSON.stringify({email:f.elements.email.value})});
    status.textContent=res.message;
    if(res.dev_reset_url){
      const devBox=$('#dev-reset-box');
      const devLink=$('#dev-reset-link');
      devLink.href=res.dev_reset_url;
      devBox.classList.remove('hidden');
    }
  }catch(err){
    status.textContent=err.message;
  }finally{
    btn.disabled=false;
  }
});

// Reset Password Form
$('#reset-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget;
  const err=$('#reset-error');
  err.textContent='';
  const pw=f.elements.password.value;
  const cpw=f.elements.confirm_password.value;
  if(pw!==cpw){
    err.textContent='Passwords do not match.';
    return;
  }
  const btn=$('#reset-submit');
  btn.disabled=true;
  try{
    const res=await api('/reset-password',{
      method:'POST',
      body:JSON.stringify({
        token:f.elements.token.value,
        password:pw,
        confirm_password:cpw
      })
    });
    $('#reset-modal').classList.add('hidden');
    window.history.replaceState({},document.title,window.location.pathname);
    notify(res.message);
    openAuth('login');
  }catch(e){
    err.textContent=e.message;
  }finally{
    btn.disabled=false;
  }
});

// Profile Form
$('#profile-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const status=$('#profile-status');
  status.textContent='Saving…';
  try{
    const d=await api('/profile',{method:'PUT',body:JSON.stringify(profilePayload())});
    state.profile=d.profile;
    if(d.user)state.user=d.user;
    status.textContent='Saved';
    await updateMetrics();
    await loadOverview();
    setTimeout(()=>status.textContent='',2500);
  }catch(err){
    status.textContent=err.message;
  }
});

// Change Password Form in Profile
const changePwForm=$('#change-password-form');
if(changePwForm){
  changePwForm.addEventListener('submit',async e=>{
    e.preventDefault();
    const f=e.currentTarget;
    const status=$('#change-password-status');
    status.textContent='Updating…';
    try{
      const res=await api('/change-password',{
        method:'PUT',
        body:JSON.stringify({
          current_password:f.elements.current_password.value,
          new_password:f.elements.new_password.value,
          confirm_password:f.elements.confirm_password.value
        })
      });
      status.textContent=res.message;
      f.reset();
      notify('Password changed successfully.');
      setTimeout(()=>status.textContent='',3000);
    }catch(err){
      status.textContent=err.message;
    }
  });
}

// Workout Form
$('#workout-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget,data=Object.fromEntries(new FormData(f));
  data.duration_minutes=Number(data.duration_minutes);
  try{
    await api('/workouts',{method:'POST',body:JSON.stringify(data)});
    f.reset();
    f.elements.exercise_date.value=new Date().toISOString().slice(0,10);
    notify('Workout saved. Nice work showing up.');
    await loadWorkouts();
    await loadOverview();
  }catch(err){notify(err.message,true)}
});

// Edit Workout Form
const editWorkoutForm=$('#edit-workout-form');
if(editWorkoutForm){
  editWorkoutForm.addEventListener('submit',async e=>{
    e.preventDefault();
    const f=e.currentTarget;
    const err=$('#edit-workout-error');
    err.textContent='';
    const id=f.elements.id.value;
    const data={
      exercise_type:f.elements.exercise_type.value,
      duration_minutes:Number(f.elements.duration_minutes.value),
      exercise_date:f.elements.exercise_date.value,
      notes:f.elements.notes.value
    };
    try{
      await api('/workouts/'+id,{method:'PUT',body:JSON.stringify(data)});
      $('#edit-workout-modal').classList.add('hidden');
      notify('Workout updated.');
      await loadWorkouts();
      await loadOverview();
    }catch(e){
      err.textContent=e.message;
    }
  });
}

// Weight Check-in Form
$('#weight-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget,d=Object.fromEntries(new FormData(f));
  d.weight_kg=Number(d.weight_kg);
  try{
    await api('/progress',{method:'POST',body:JSON.stringify(d)});
    f.elements.weight_kg.value='';
    notify('Check-in saved.');
    await loadProgress();
    await loadOverview();
  }catch(err){notify(err.message,true)}
});

// Model Prediction Form
$('#dataset-predict-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget,d=Object.fromEntries(new FormData(f));
  d.duration_minutes=Number(d.duration_minutes);
  d.daily_steps=Number(d.daily_steps);
  const output=$('#dataset-prediction-result');
  output.textContent='Estimating…';
  try{
    const r=await api('/model-prediction',{method:'POST',body:JSON.stringify(d)});
    output.textContent=`Dataset fitness-level score estimate: ${r.result.prediction} · held-out MAE ${r.result.evaluation.mae}. ${r.result.disclaimer}`;
  }catch(err){
    output.textContent=err.message;
    notify(err.message,true);
  }
});

$('#apply-filter').addEventListener('click',()=>loadProgress());
$('#chat-form').addEventListener('submit',e=>{e.preventDefault();sendChat(e.currentTarget.elements.message.value)});

$('#logout').addEventListener('click',async()=>{
  await api('/logout',{method:'POST'}).catch(()=>{});
  state.user=null;
  state.profile=null;
  showLanding();
  notify('You’re signed out.');
});

$('#delete-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const f=e.currentTarget;
  try{
    await api('/account',{method:'DELETE',body:JSON.stringify({password:f.elements.password.value,confirmation:f.elements.confirmation.checked})});
    $('#confirm-modal').classList.add('hidden');
    state.user=null;
    showLanding();
    notify('Account and associated records deleted.');
  }catch(err){
    $('#delete-error').textContent=err.message;
  }
});

document.addEventListener('DOMContentLoaded',()=>{
  const today=todayISO();
  for(const id of ['workout-form','weight-form']){
    const input=$(`#${id} input[type=date]`);
    if(input)input.value=today;
  }
  start();
});
