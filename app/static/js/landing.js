// Nav scroll
    const nav = document.getElementById('nav');
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 50);
    });

    // Scroll reveal
    const revealElements = document.querySelectorAll('.reveal');
    const revealObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry, index) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.classList.add('visible');
          }, index * 100);
        }
      });
    }, { threshold: 0.1 });
    revealElements.forEach(el => revealObserver.observe(el));

    // Smooth scroll for nav links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({ behavior: 'smooth' });
      });
    });

    // Load stats dynamically
    async function loadStats(){
      try {
        const r = await fetch('/api/calculos/stats');
        if(r.ok){
          const d = await r.json();
          document.getElementById('stat-tiendas').textContent = d.tiendas || '5+';
          document.getElementById('stat-mezclas').textContent = d.mezclas || '12';
          document.getElementById('stat-mamposterias').textContent = d.mamposterias || '37';
        }
      } catch(e){}
    }
    loadStats();