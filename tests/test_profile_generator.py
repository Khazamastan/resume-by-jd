from dataclasses import asdict

from resume_builder.models import ReferenceStructure, ResumeSection, Theme
from resume_builder.profile_generator import build_profile_from_reference


def test_build_profile_from_reference_returns_sample_profile():
    reference = ReferenceStructure(theme=Theme(), sections=[ResumeSection(title="Reference")])

    profile = build_profile_from_reference(reference)
    profile_dict = asdict(profile)

    expected = {
        "name": "Khajamastan Bellamkonda",
        "headline": "Principal Member Technical Staff",
        "contact": {
            "phone": "+91-7207810602",
            "email": "khazamastan@gmail.com",
            "location": "Bangalore, India",
            "linkedin": "https://www.linkedin.com/in/khazamastan",
        },
        "summary": [
            "Principal-level front-end engineer with 10+ years delivering large-scale web applications for global product companies.",
            "Strong focus on React ecosystems, micro front-ends, and resilient CI/CD pipelines that improve performance and developer velocity.",
            "Proven track record aligning user experience with business goals while raising code quality and test coverage.",
        ],
        "experience": [
            {
                "company": "Oracle",
                "role": "Principal Member Technical Staff",
                "location": "Bangalore, KA",
                "start": "2022-04-01",
                "end": "Present",
                "bullets": [
                    "Revamped Redwood-themed notification emails and Alloy customization options, increasing customer engagement by 20%.",
                    "Implemented cross-region disaster recovery workflows to maintain 100% operational continuity during outages.",
                    "Bootstrapped MAUI-based next-gen Identity console, cutting maintenance effort by 40% and accelerating feature delivery by 30%.",
                    "Redesigned MFA sign-on policy to gather customer consent and alert administrators, strengthening security posture.",
                    "Migrated TeamCity pipelines to OCI build systems, unified repositories in OCI DevOps SCM, and automated canary health checks every 15 minutes.",
                    "Consolidated multiple profile experiences into the reusable One My Profile UI, reducing development effort by 60%.",
                    "Integrated Apple as a social identity provider to expand authentication options.",
                    "Delivered UI for National Digital Identity features, including Identity Proofing, Verification Provider, Credential Type, and Digital Wallet workflows.",
                    "Raised React test coverage from 39% to 70% using React Testing Library and Jest while authoring functional requirements with product managers.",
                ],
            },
            {
                "company": "Xactly Corp",
                "role": "Senior Software Developer",
                "location": "Bangalore, KA",
                "start": "2021-06-01",
                "end": "2022-04-01",
                "bullets": [
                    "Migrated front-end builds to Webpack with code splitting, improving load times by 20–30%.",
                    "Led the React and TypeScript Objectives product, bootstrapping the codebase, end-to-end tests, and CI/CD deployments.",
                    "Built the Incent module for incentive compensation using React.js, Node.js, Angular, and Webpack.",
                    "Created a config-driven React framework that accelerates Objectives UI delivery.",
                ],
            },
            {
                "company": "Nineleaps",
                "role": "Software Development Engineer II",
                "location": "Bangalore, KA",
                "start": "2020-05-01",
                "end": "2021-06-01",
                "bullets": [
                    "Migrated legacy apps to a micro front-end architecture via Module Federation for seamless integration.",
                    "Built a config-based React component framework that renders UI from declarative definitions.",
                    "Delivered Vendor Management System modules such as Interview, Onboarding, Performance, and Exit using React.js, Node.js, Webpack, Styled Components, and Cypress.",
                    "Automated build and deployment pipelines to improve development efficiency and application performance.",
                    "Added Cypress-driven unit and end-to-end testing to raise reliability.",
                ],
            },
            {
                "company": "PWC",
                "role": "Senior Software Engineer",
                "location": "Bangalore, KA",
                "start": "2018-07-01",
                "end": "2020-05-01",
                "bullets": [
                    "Led development of a cybersecurity digital risk management dashboard for Fortune 500 clients.",
                    "Migrated a legacy Aurelia application to React to streamline engineering workflows.",
                    "Instituted development best practices that improved code quality across the team.",
                    "Moved the build system to Webpack, cutting bundle size by 50% and improving load times by 30–40%.",
                ],
            },
            {
                "company": "Minewhat Inc",
                "role": "Senior Front-End Developer",
                "location": "Bangalore, KA",
                "start": "2016-08-01",
                "end": "2018-07-01",
                "bullets": [
                    "Owned user experience for an ML-driven e-commerce recommendation platform reporting to the CTO.",
                    "Built recommendation widgets and banners with React.js, MobX, SCSS, and Stylus.",
                    "Created a visual editor for customers to live-edit and theme widgets to match site branding.",
                    "Developed frameworks for sliders, placement tools, inline text editing, and templated SVG banners.",
                ],
            },
            {
                "company": "Thrymr Software",
                "role": "UI Developer",
                "location": "Bangalore, KA",
                "start": "2015-02-01",
                "end": "2016-08-01",
                "bullets": [
                    "Built the iStyle room designer application with a points system using JavaScript, Canvas, Angular, and Fabric.js.",
                    "Developed the Thrymr Internal Portal for collaboration, notifications, attendance, and leave management.",
                    "Maintained a weight-loss program dashboard with recipe authoring, diet planning, and weight tracking features.",
                ],
            },
        ],
        "education": [
            {
                "institution": "Rajiv Gandhi University of Knowledge Technologies",
                "degree": "B.Tech in Mechanical Engineering",
                "location": "R.K. Valley, Andhra Pradesh",
                "start": "2010-08-01",
                "end": "2014-05-01",
                "details": [],
            }
        ],
        "projects": [],
        "certifications": [],
        "skills": [
            "JavaScript",
            "Node.js",
            "React",
            "Redux",
            "Mobx",
            "Webpack",
            "HTML/CSS",
            "Web Accessibility",
            "Material-UI",
            "Micro front-ends",
            "Docker",
            "Git",
            "React Testing Library",
            "Jest",
            "Cypress",
            "Styled Components",
            "CI/CD",
            "NoSQL",
        ],
        "additional_sections": [
            {
                "title": "Awards",
                "bullets": [
                    "Won Thrymr Software Spot Award for Best Performance.",
                    "Named 2021 Tech Champion by Nineleaps Technology Solutions.",
                    "Received Nineleaps Feather On the Hat award in January 2021.",
                ],
                "paragraphs": [],
                "meta": {},
            }
        ],
    }

    assert profile_dict == expected
