import { useNavigate } from 'react-router-dom';
import type { Project } from '@/types';
import './ProjectCard.css';

interface ProjectCardProps {
  project: Project;
  onDelete: () => void;
}

export default function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const navigate = useNavigate();

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const handleClick = () => {
    navigate(`/projects/${project.id}`);
  };

  return (
    <div className="project-card" onClick={handleClick}>
      <div className="project-card-header">
        <h3 className="project-name">{project.name}</h3>
        <button
          className="delete-btn"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          title="Delete project"
        >
          ×
        </button>
      </div>

      <p className="project-description">
        {project.description || 'No description'}
      </p>

      <div className="project-card-footer">
        <span className="project-date">
          Updated {formatDate(project.updated_at)}
        </span>
      </div>
    </div>
  );
}
